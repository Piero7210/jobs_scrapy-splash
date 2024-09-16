import scrapy
from scrapy_splash import SplashRequest
from datetime import datetime, timedelta
from job_scraper.items import JobItem
from job_scraper.utils.sql_alchemy import Job, SessionLocal
from job_scraper.utils.sql_alchemy_pre_db import PreJob
from sqlalchemy.exc import SQLAlchemyError
from job_scraper.utils.description_extraction import get_keywords
import traceback

class BumeranSpider(scrapy.Spider):
    name = "bumeran_spider"
    allowed_domains = ["bumeran.com.pe", "localhost"]
    start_urls = []

    # Generar las URLs iniciales para cada palabra clave
    def __init__(self, *args, **kwargs):
        super(BumeranSpider, self).__init__(*args, **kwargs)
        # keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo', 'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 'Vendedor', 'Promotor', 'Atencion']
        keywords_jobs = ['Asistente']
        self.start_urls = [
            f'https://www.bumeran.com.pe/empleos-publicacion-menor-a-7-dias-busqueda-{keyword}.html?recientes=true&page={i}'
            for keyword in keywords_jobs for i in range(1, 3)
        ]

    def start_requests(self):
        """
        Generates scrapy Requests for the start_urls and yields SplashRequests.

        Yields:
            SplashRequest: A scrapy Request with Splash parameters.
        """       
        for url in self.start_urls:
            yield SplashRequest(
                url,
                self.parse,
                endpoint='render.html',
                args={'wait': 10,
                      'html': 1,
                },
            )            

    def parse(self, response):
        """
        Parse the response from the website and extract job information.
        Args:
            response (scrapy.http.Response): The response object containing the HTML.
        Returns:
            None
        """
        self.log(f"URL: {response.url}, HTTP Status: {response.status}")

        # Obtiene los elementos de la página
        company_elements = response.css('h3.sc-kIXKos.fxWEQZ') # Ajustar el selector según tu HTML (suele cambiar)
        print(f'Company: {company_elements}')
        title_elements = response.css('h3.sc-dCVVYJ.kpFBFp') # Ajustar el selector según tu HTML (suele cambiar)
        print(f'Title: {title_elements}')
        location_elements = response.css('h3.sc-LAuEU.hhLLAT')[::2] # Ajustar el selector según tu HTML (suele cambiar)
        print(f'Location: {location_elements}')
        date_elements = response.css('h3.sc-fGSyRc.cCgKJg') # Ajustar el selector según tu HTML (suele cambiar)
        print(f'Date: {date_elements}')

        if not company_elements or not title_elements or not location_elements or not date_elements:
            self.log("No more jobs found, ending pagination.")
            return

        for job in range(min(len(company_elements), len(title_elements), len(location_elements), len(date_elements))):
            item = JobItem()
            try:
                # Obtiene el nombre de la empresa
                item['company'] = company_elements[job].xpath(
                    ".//text()").get().strip()

                # Obtiene el título del empleo
                item['title'] = title_elements[job].xpath(
                    ".//text()").get().strip()

                # Obtiene la ubicación del empleo
                item['location'] = location_elements[job].xpath(
                    ".//text()").get().strip()

                # Obtiene la fecha de publicación del empleo
                job_date_text = date_elements[job].xpath(
                    ".//text()").get().strip()
                item['date'] = self.convert_to_date(job_date_text)

                # Obtiene la URL de la descripción del empleo
                job_description_href = response.css(
                    'a.sc-kJdAmE.etbjmW::attr(href)').getall()[job]
                item['link_url'] = response.urljoin(job_description_href)

                item['platform'] = 'Bumeran'
                item['date_scraped'] = datetime.now().strftime("%Y-%m-%d")
                item['keyword'] = response.url.split(
                    '/')[-1].split('-')[-1].split('.')[0]

                # Realizar una solicitud para obtener la descripción del empleo
                yield SplashRequest(
                    url=item['link_url'],
                    callback=self.parse_job_description,
                    meta={'item': item},
                    args={'wait': 10}
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
        """
        item = response.meta['item']

        try:
            # Extracción de la descripción del empleo
            job_description = response.css('div.sc-jYIdPM.kTYgTC p::text, div.sc-jYIdPM.kTYgTC li::text').getall()
            job_description = "\n".join([desc.strip() for desc in job_description])
            item['description'] = job_description

            # Extracción del tipo de empleo (debes ajustar el índice según tu HTML)
            type_of_job = response.css('h2.sc-gAjsMU.coOCyB::text').getall()[4].strip().split(',')[0] # Ajustar el selector según tu HTML (suele cambiar)

            # Obtiene las palabras clave de la descripción del empleo
            result_keywords = get_keywords(job_description, item['title'], item['company'], item['location'])
            if not result_keywords or not isinstance(result_keywords, dict):
                self.logger.error("Failed to retrieve keywords or invalid response structure")
                return

            # Formatea los resultados
            item['soft_skills'] = ', '.join(result_keywords.get(
                'Soft skills', [])) if result_keywords else 'N/A'
            item['hard_skills'] = ', '.join(result_keywords.get(
                'Hard skills', [])) if result_keywords else 'N/A'
            item['education'] = ', '.join(result_keywords.get(
                'Nivel educativo', [])) if result_keywords else 'N/A'
            item['careers'] = ', '.join(result_keywords.get(
                'Profesiones', [])) if result_keywords else 'N/A'
            item['lgtbq'] = str(result_keywords.get(
                'LGBTQ+', False)) if result_keywords else 'False'
            item['seniority'] = str(result_keywords.get(
                'Seniority', 'no especificado')) if result_keywords else 'no especificado'
            item['work_mode'] = str(result_keywords.get(
                'Modalidad de trabajo', 'Presencial')) if result_keywords else 'Presencial'
            item['type_of_job'] = type_of_job

        except Exception as e:
            self.logger.error(f"Error al procesar la descripción del empleo: {e}")
            self.logger.error(traceback.format_exc())
            return None

        # Guardar los datos en la base de datos
        self.save_pre_db(item)
        self.save_to_db(item)

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
                platform=item['platform'],
                description=item['description'],
                link_url=item['link_url'],
                keyword=item['keyword'],
                state=1,
                date_scraped=item['date_scraped']
            )
            session.add(job_record)
            session.commit()
            self.logger.info(
                f"Pre Item successfully saved to DB: {item['title']} at {item['company']}")
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
        None
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
        Converts a given date text into a datetime object.

        Parameters:
        - date_text (str): The date text to be converted.

        Returns:
        - datetime: The converted datetime object.

        Example:
        >>> convert_to_date('hoy')
        datetime.datetime(2022, 9, 1, 12, 0)
        """
        today = datetime.now()
        date_text = date_text.lower()
        if 'hoy' in date_text:
            return today
        elif 'ayer' in date_text:
            return today - timedelta(days=1)
        elif 'hora' in date_text:
            hours = int(''.join(filter(str.isdigit, date_text)))
            return today - timedelta(hours=hours)
        elif 'día' in date_text or 'días' in date_text:
            days = int(''.join(filter(str.isdigit, date_text)))
            return today - timedelta(days=days)
        else:
            return today
