import scrapy
from scrapy_splash import SplashRequest
from datetime import datetime, timedelta
from job_scraper.items import JobItem
from job_scraper.utils.sql_alchemy import Job, SessionLocal  # Asegúrate de que esté bien configurado
from job_scraper.utils.sql_alchemy_pre_db import PreJob
from sqlalchemy.exc import SQLAlchemyError
from job_scraper.utils.description_extraction import get_keywords # Importa la función OpenAI Api
import traceback

class IndeedSpider(scrapy.Spider):
    name = "indeed_spider"
    allowed_domains = ["indeed.com", "localhost"]
    start_urls = []

    # Generar las URLs iniciales para cada palabra clave
    def __init__(self, *args, **kwargs):
        super(IndeedSpider, self).__init__(*args, **kwargs)
        # keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo', 'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 'Vendedor', 'Promotor', 'Atencion']
        keywords_jobs = ['Data']
        for keyword in keywords_jobs:
            self.start_urls.extend([f'https://pe.indeed.com/jobs?q={keyword}&l=Lima&sort=date&fromage=7&start={i}' for i in range(0, 70, 10)])
            
    def start_requests(self):
        """
        Generates scrapy Requests for each URL in the start_urls list.
        
        Yields:
            SplashRequest: A scrapy Request object with SplashRequest parameters.
        """
        for url in self.start_urls:
            yield SplashRequest(url, self.parse, args={'wait': 5}, endpoint='render.html')

    def parse(self, response):
        """
        Parse the response from the website and extract job information.
        Args:
            response (scrapy.http.Response): The response object from the website.
        Yields:
            scrapy.Request: A request object to scrape the job description.
        Returns:
            None
        """
        job_page = response.css('#mosaic-jobResults')
        jobs = job_page.css('div.job_seen_beacon')
        
        if not jobs:
            self.log("No more jobs found, ending pagination.")
            return
        
        for job in jobs:
            item = JobItem()
            try:
                # Obtiene el título del empleo
                job_title_element = job.css('h2.jobTitle span::text').get()
                item['title'] = job_title_element.strip() if job_title_element else None
                
                # Obtiene el nombre de la empresa
                company_title = job.css('div.css-1qv0295 span::text').get()
                item['company'] = company_title.strip() if company_title else None
                
                # Obtiene la ubicación del empleo
                job_location = job.css('div.css-1p0sjhy::text').get()
                item['location'] = job_location.strip() if job_location else None
                
                # Obtiene la fecha de publicación del empleo
                job_date = job.css('span.css-qvloho::text').get()
                item['date'] = self.convert_to_date(job_date)
                
                # Obtiene la URL de la descripción del empleo
                job_description_href = job.css('h2.jobTitle a::attr(href)').get()
                item['link_url'] = response.urljoin(job_description_href)
                
                item['platform'] = 'Indeed'
                item['date_scraped'] = datetime.now().strftime("%Y-%m-%d")
                item['keyword'] = 'data'  # Palabra clave utilizada para la búsqueda

                # Realizar una solicitud para obtener la descripción del empleo
                yield SplashRequest(
                    url=item['link_url'],
                    callback=self.parse_job_description,
                    meta={'item': item},
                    args={'wait': 5}
                )
            except Exception as e:
                self.log(f"Se produjo un error en el bucle: {e}")
                continue

    def parse_job_description(self, response):
        """
        Parses the job description from the response and extracts relevant information.
        Args:
            response (scrapy.http.Response): The response object containing the job description.
        Returns:
            None: If there is an error processing the job description.
            None: If the keywords retrieval fails or the response structure is invalid.
            None: If the job description is not found in the response.
        """
        item = response.meta['item']
        
        try:
            # Inicializa una lista para almacenar los párrafos
            job_description_paragraphs = []        
            # Encuentra el div objetivo
            target_div = response.css('div.jobsearch-JobComponent-description').get()
            # Itera sobre los elementos dentro del target_div
            if target_div:
                for element in response.css('div.jobsearch-JobComponent-description p, div.jobsearch-JobComponent-description li'):
                    job_description_paragraphs.append(element.get().strip())                                
            # Combina los párrafos en una sola cadena
            job_description = '\n'.join(job_description_paragraphs)
            item['description'] = job_description
                    
            # Selecciona el tercer <h2> (ajusta el índice según sea necesario)
            type_of_job = response.css('div.js-match-insights-provider-tvvxwd.ecydgvn1::text').get()
            if type_of_job in ['Tiempo completo', 'Tiempo parcial', 'Por contrato', 'Indefinido', 'Temporal', 'Medio tiempo']:
                type_of_job = type_of_job.strip()
            else:
                type_of_job = response.css('div.js-match-insights-provider-tvvxwd.ecydgvn1::text').get_all()[1].strip()
            
            # Obtiene las palabras clave de la descripción del empleo
            result_keywords = get_keywords(job_description, item['title'], item['company'], item['location'])
            if not result_keywords or not isinstance(result_keywords, dict):
                print("Failed to retrieve keywords or invalid response structure")
                return None
            
            # Formatea los resultados
            item['soft_skills'] = ', '.join(result_keywords.get('Soft skills', [])) if result_keywords else 'N/A'
            item['hard_skills'] = ', '.join(result_keywords.get('Hard skills', [])) if result_keywords else 'N/A'
            item['education'] = ', '.join(result_keywords.get('Nivel educativo', [])) if result_keywords else 'N/A'
            item['careers'] = ', '.join(result_keywords.get('Profesiones', [])) if result_keywords else 'N/A'
            item['lgtbq'] = str(result_keywords.get('LGBTQ+', False)) if result_keywords else 'False'
            item['seniority'] = str(result_keywords.get('Seniority', 'no especificado')) if result_keywords else 'no especificado'
            item['work_mode'] = str(result_keywords.get('Modalidad de trabajo', 'Presencial')) if result_keywords else 'Presencial'
            item['type_of_job'] = type_of_job
            
            # Guardar los datos en la base de datos
            self.save_pre_db(item) # Guarda el item sin usar GPT-3.5
            self.save_to_db(item)
    
        except Exception as e:
            self.logger.error(f"Error al procesar la descripción del empleo: {e}")
            self.logger.error(traceback.format_exc())
            return None
        
    
    def save_pre_db(self, item):
        """
        Saves only the item without the use of GPT-3.5.

        Args:
            item (dict): The item to be saved.

        Returns:
            None
        """
        session = SessionLocal()
        try:
            job_record = PreJob(
                company_name=item['company'],
                job_title=item['title'],
                location=item['location'],
                date=item['date'],
                type_of_job=item.get('type_of_job'),
                description=item['description'],
                platform=item['platform'],
                link_url=item['link_url'],
                keyword=item['keyword'],
                state=1,
                date_scraped=item['date_scraped']
            )
            session.add(job_record)
            session.commit()
            self.logger.info(f"Pre Item successfully saved to DB: {item['title']} at {item['company']}")
        except SQLAlchemyError as e:
            self.log(f"Error occurred during commit: {e}")
            session.rollback()
        finally:
            session.close()
        
    def save_to_db(self, item):
        """
        Saves the scraped job data to the database.

        Parameters:
        - item (dict): A dictionary containing the job data.

        Returns:
        - None

        Raises:
        - SQLAlchemyError: If an error occurs during the database commit.

        """
        session = SessionLocal()
        try:
            job_record = Job(
                company_name=item['company'],
                job_title=item['title'],
                location=item['location'],
                date=item['date'],
                soft_skills=item.get('soft_skills'),
                hard_skills=item.get('hard_skills'),
                education=item.get('education'),
                careers=item.get('careers'),
                seniority=item.get('seniority'),
                type_of_job=item.get('type_of_job'),
                work_mode=(item.get('work_mode') or 'Presencial'),
                lgtbq=item.get('lgtbq'),
                platform=item['platform'],
                link_url=item['link_url'],
                keyword=item['keyword'],
                state=1,
                date_scraped=item['date_scraped']
            )
            session.add(job_record)
            session.commit()
        except SQLAlchemyError as e:
            self.log(f"Error occurred during commit: {e}")
            session.rollback()
        finally:
            session.close()

    def convert_to_date(self, date_text):
        """
        Converts a given date text to a datetime object.
        Parameters:
        - date_text (str): The date text to be converted.
        Returns:
        - datetime: The converted datetime object.
        Example:
        >>> convert_to_date('recien publicado')
        datetime.datetime(2022, 9, 15, 12, 0)  # Assuming today is September 15, 2022
        >>> convert_to_date('2 dias')
        datetime.datetime(2022, 9, 13, 12, 0)  # Assuming today is September 15, 2022
        """
        today = datetime.now()
        date_text = date_text.lower()

        if 'recien publicado' in date_text:
            return today
        elif 'dia' in date_text or 'dias' in date_text:
            days = int(date_text.split()[0])  # Obtiene el número de días del texto
            return today - timedelta(days=days)
        else:
            return today