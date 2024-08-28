import time
import requests
import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from sqlalchemy.exc import SQLAlchemyError
from job_scraper.utils.description_extraction import get_keywords # Importa la función OpenAI Api
from job_scraper.utils.sql_alchemy import Job, SessionLocal
from job_scraper.items import JobItem
import traceback

class LinkedinSpider(scrapy.Spider):
    name = 'linkedin_spider'
    keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo', 
                     'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 
                     'Vendedor', 'Promotor', 'Atencion']

    def start_requests(self):
        for keyword in self.keywords_jobs:
            url_linkedin = f'https://www.linkedin.com/jobs/search?keywords={keyword}&location=Lima%2C%20Per%C3%BA&geoId=101312395&distance=25&f_TPR=r604800&position=1&pageNum=0'
            yield SeleniumRequest(
                url=url_linkedin,
                callback=self.parse,
                meta={'keyword': keyword},
                wait_time=10
            )

    def parse(self, response):
        driver = response.meta['driver']
        keyword = response.meta['keyword']

        # Obtiene el número de empleos
        try:
            number_of_jobs = int(driver.find_element(By.CLASS_NAME, 'results-context-header__job-count').text)
            self.logger.info(f"Number of jobs for keyword '{keyword}': {number_of_jobs}")
        except Exception as e:
            self.logger.error(f"Error retrieving job count: {e}")
            return

        # Realiza scroll en la página para cargar más empleos
        scroll = 0
        while scroll < number_of_jobs // 25:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            scroll += 1
            try:
                button_found = driver.find_element(By.XPATH, "//button[@aria-label='Ver más empleos']")
                if button_found:
                    driver.execute_script("arguments[0].click();", button_found)
                    time.sleep(2)
                else:
                    break
            except Exception as e:
                self.logger.error(f"Error during scrolling: {e}")
                break

        jobs_data = []

        # Recoge los datos de los empleos
        company_elements = driver.find_elements(By.CLASS_NAME, 'base-search-card__subtitle')
        title_elements = driver.find_elements(By.CLASS_NAME, 'base-search-card__title')
        location_elements = driver.find_elements(By.CLASS_NAME, 'job-search-card__location')
        date_elements = driver.find_elements(By.TAG_NAME, 'time')

        for i in range(min(number_of_jobs, len(company_elements), len(title_elements), len(location_elements), len(date_elements))):
            try:
                item = JobItem()
                item['company'] = company_elements[i].text
                item['title'] = title_elements[i].text
                item['location'] = location_elements[i].text
                item['date'] = date_elements[i].get_attribute('datetime')
                item['platform'] = 'LinkedIn'
                item['link_url'] = driver.find_elements(By.CLASS_NAME, 'base-card__full-link')[i].get_attribute('href')
                item['keyword'] = keyword
                item['date_scraped'] = time.strftime("%Y-%m-%d")

                # Obtiene la descripción del empleo
                description_result = get_keywords(item['link_url'], item['title'], item['company'], item['location'])
                time.sleep(2)
                if description_result is None or not isinstance(description_result, dict):
                    self.logger.error(f"Error al obtener la descripción del empleo desde {item['link_url']}")
                    continue

                # Combina los datos obtenidos con los datos del item
                item.update(description_result)
                item['state'] = 1  # Marcamos como activo
                
                jobs_data.append(dict(item))  # Convertimos el item a dict para guardar

            except Exception as e:
                self.logger.error(f"Se produjo un error en el bucle: {e}")
                continue

        # Guardar los datos en la base de datos
        self.save_to_db(jobs_data)
        
    def parse_job_description(self, response):
        max_retries = 5  # Número máximo de reintentos
        backoff_factor = 2  # Factor de retroceso exponencial
        delay = 1  # Tiempo inicial de espera en segundos
        
        for attempt in range(max_retries):
            try:
                # Realiza una solicitud GET a la URL de la descripción del empleo
                response = requests.get(job_description_href)
                print(f"Response status code: {response.status_code}")  # Imprime el código de estado de la respuesta

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    time.sleep(0.5) 
                    # Obtiene la descripción del empleo
                    job_description = soup.find('div', class_='show-more-less-html__markup').get_text(separator="\n").strip()
                    # Obtiene el tipo de empleo
                    type_of_job = soup.find_all('h3', class_='description__job-criteria-subheader')[1].find_next_sibling('span').get_text()
                    # Obtiene las palabras clave de la descripción del empleo      
                    result_keywords = get_keywords(job_description, job_data['title'], job_data['company'], job_data['location'])
                    time.sleep(1)
                    if not result_keywords or not isinstance(result_keywords, dict):
                        print("Failed to retrieve keywords or invalid response structure")
                        return None
                    
                    # Formatea los resultados
                    result = {
                        'soft_skills': ', '.join(result_keywords.get('Soft skills', [])) if result_keywords else 'N/A',
                        'hard_skills': ', '.join(result_keywords.get('Hard skills', [])) if result_keywords else 'N/A',
                        'education': ', '.join(result_keywords.get('Nivel educativo', [])) if result_keywords else 'N/A',
                        'careers': ', '.join(result_keywords.get('Profesiones', [])) if result_keywords else 'N/A',
                        'lgtbq': str(result_keywords.get('LGBTQ+', False)) if result_keywords else 'False',
                        'seniority': str(result_keywords.get('Seniority', 'no especificado')) if result_keywords else 'no especificado',
                        'type_of_job': type_of_job.strip(),
                    }
                    print(result)
                    print('-----------------------------------')
                    return result
                
                elif response.status_code == 429:
                    print(f"Error 429: Demasiadas solicitudes. Esperando {delay} segundos antes de reintentar...")
                    time.sleep(delay)
                    delay *= backoff_factor  # Incrementa el tiempo de espera de forma exponencial
                else:
                    print(f"Failed to retrieve job description page: {response.status_code}")
                    return None
            
            except Exception as e:
                print(f"Error al obtener la descripción del empleo: {e}")
                print(traceback.format_exc())
                return None
        
        print("Se alcanzó el número máximo de reintentos. No se pudo obtener la descripción del empleo.")
        return None

    def save_to_db(self, jobs_data):
        session = SessionLocal()
        try:
            for job in jobs_data:
                job_record = Job(
                    company_name=job['company'],
                    job_title=job['title'],
                    location=job['location'],
                    date=job['date'],
                    soft_skills=job.get('soft_skills'),
                    hard_skills=job.get('hard_skills'),
                    education=job.get('education'),
                    careers=job.get('careers'),
                    seniority=job.get('seniority'),
                    type_of_job=job.get('type_of_job'),
                    lgtbq=job.get('lgtbq'),
                    platform=job['platform'],
                    link_url=job['link_url'],
                    keyword=job['keyword'],
                    state=job['state'],
                    date_scraped=job['date_scraped']
                )
                session.add(job_record)
            session.commit()
        except SQLAlchemyError as e:
            self.logger.error(f"Error occurred during commit: {e}")
            session.rollback()
        finally:
            session.close()
