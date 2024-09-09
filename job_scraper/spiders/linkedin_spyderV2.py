import scrapy
from datetime import datetime
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from sqlalchemy.exc import SQLAlchemyError
from job_scraper.utils.description_extraction import get_keywords
from job_scraper.utils.sql_alchemy import Job, SessionLocal
from job_scraper.utils.sql_alchemy_pre_db import PreJob
from job_scraper.items import JobItem


class LinkedinSpider(scrapy.Spider):
    name = 'linkedin_spiderV2'
    allowed_domains = ["linkedin.com", "pe.linkedin.com"]
    # keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo',                   'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 'Vendedor', 'Promotor', 'Atencion']
    start_urls = []
    date_scraped = datetime.now().strftime("%Y-%m-%d")
    
    # Generar las URLs iniciales para cada palabra clave
    # def __init__(self, *args, **kwargs):
    #     super(LinkedinSpider, self).__init__(*args, **kwargs)
    #     # keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo', 'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 'Vendedor', 'Promotor', 'Atencion']
    #     keywords_jobs = ['Asistente']
    #     for keyword in keywords_jobs:
    #         self.start_urls.extend([f'https://www.linkedin.com/jobs/search?keywords={keyword}&location=Peru&geoId=101312395&distance=25&f_TPR=r604800&position=1&pageNum=0'])
    
    def start_requests(self):
        url = 'https://www.linkedin.com/jobs/search?keywords=Asistente&location=Peru&geoId=101312395&distance=25&f_TPR=r604800&position=1&pageNum=0'
        yield SeleniumRequest(
            url=url,
            wait_time=10,
            screenshot=True,
            callback=self.parse,
            meta={'keyword': url.split('=')[1].split('&')[0]},
        )

    def parse(self, response):
        keyword = response.meta['keyword']

        # Obtiene el número de empleos
        try:
            number_of_jobs = int(response.css('.results-context-header__job-count::text').get())
            self.logger.info(f"Number of jobs for keyword '{keyword}': {number_of_jobs}")
        except Exception as e:
            self.logger.error(f"Error retrieving job count: {e}")
            return

        # Recoge los datos de los empleos
        job_cards = response.css('.base-card__full-link')
        print(len(job_cards))
        print('job_cards:', job_cards)
        for card in job_cards:
            try:
                item = JobItem()
                item['company'] = card.css('.base-search-card__subtitle::text').get()
                item['title'] = card.css('.base-search-card__title::text').get()
                item['location'] = card.css('.job-search-card__location::text').get()
                item['date'] = card.css('time::attr(datetime)').get()
                item['platform'] = 'LinkedIn'
                item['link_url'] = card.css('.base-card__full-link::attr(href)').get()
                item['keyword'] = keyword
                item['date_scraped'] = self.date_scraped
                
                # Realizar una solicitud para obtener la descripción del empleo
                yield SeleniumRequest(
                    url=item['link_url'],
                    callback=self.parse_job_description,
                    meta={'item': item},
                )

            except Exception as e:
                self.logger.error(f"Se produjo un error en el bucle: {e}")
                continue
            
    def parse_job_description(self, response):
        item = response.meta['item']

        try:
            # Obtiene la descripción del empleo
            job_description = response.css('div.show-more-less-html__markup *::text').getall()
            job_description = '\n'.join([desc.strip() for desc in job_description]).strip()

            # Obtiene el tipo de empleo
            type_of_job = response.css('h3.description__job-criteria-subheader + span::text').get()
            type_of_job = type_of_job.strip() if type_of_job else 'N/A'

            # Obtiene las palabras clave de la descripción del empleo
            result_keywords = get_keywords(job_description, item['title'], item['company'], item['location'])

            if not result_keywords or not isinstance(result_keywords, dict):
                self.logger.error("Failed to retrieve keywords or invalid response structure")
                return None

            # Formatea los resultados y los añade al item
            item['soft_skills'] = ', '.join(result_keywords.get('Soft skills', [])) if result_keywords else 'N/A'
            item['hard_skills'] = ', '.join(result_keywords.get('Hard skills', [])) if result_keywords else 'N/A'
            item['education'] = ', '.join(result_keywords.get('Nivel educativo', [])) if result_keywords else 'N/A'
            item['careers'] = ', '.join(result_keywords.get('Profesiones', [])) if result_keywords else 'N/A'
            item['lgtbq'] = str(result_keywords.get('LGBTQ+', False)) if result_keywords else 'False'
            item['seniority'] = str(result_keywords.get('Seniority', 'no especificado')) if result_keywords else 'no especificado'
            item['work_mode'] = str(result_keywords.get('Modalidad de trabajo', 'Presencial')) if result_keywords else 'Presencial'
            item['type_of_job'] = type_of_job

            # Guarda el item en PreDB y luego en la base de datos principal
            self.save_pre_db(item)  # Guarda sin usar GPT-3.5
            self.save_to_db(item)  # Guarda el item completo en la base de datos

        except Exception as e:
            self.logger.error(f"Error al obtener la descripción del empleo: {e}")
            return None

    def save_pre_db(self, item):
        """
        Guarda el item en la tabla PreJob sin usar GPT-3.5.

        Args:
            item (dict): El item a guardar.
        """
        session = SessionLocal()
        try:
            # Crea un registro del trabajo en la tabla PreJob
            pre_job_record = PreJob(
                company_name=item['company'],
                job_title=item['title'],
                location=item['location'],
                date=item['date'],
                type_of_job=item.get('type_of_job'),
                platform=item['platform'],
                description=item.get('description', ''),
                link_url=item['link_url'],
                keyword=item['keyword'],
                state=1,
                date_scraped=item['date_scraped']
            )
            session.add(pre_job_record)
            session.commit()
            self.logger.info(f"Pre Item successfully saved to DB: {item['title']} at {item['company']}")
        except SQLAlchemyError as e:
            self.logger.error(f"Error occurred during commit (PreDB): {e}")
            session.rollback()
        finally:
            session.close()

    def save_to_db(self, item):
        """
        Guarda el item completo en la base de datos principal.

        Args:
            item (dict): El item a guardar.
        """
        session = SessionLocal()
        try:
            # Crea el registro del trabajo con los campos correspondientes
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
                work_mode=item.get('work_mode', 'Presencial'),
                lgtbq=item.get('lgtbq', 'False'),
                platform=item['platform'],
                link_url=item['link_url'],
                keyword=item['keyword'],
                state=1,
                date_scraped=item['date_scraped']
            )
            session.add(job_record)
            session.commit()
            self.logger.info(f"Item successfully saved to DB: {item['title']} at {item['company']}")
        except SQLAlchemyError as e:
            self.logger.error(f"Error occurred during commit (Main DB): {e}")
            session.rollback()
        finally:
            session.close()