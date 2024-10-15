import scrapy
from scrapy_splash import SplashRequest
from datetime import datetime, timedelta
from job_scraper.items import JobItem
from job_scraper.utils.sql_alchemy_pre_db import PreJob, SessionLocal
from sqlalchemy.exc import SQLAlchemyError
import traceback

class IndeedSpider(scrapy.Spider):
    name = "indeed_spider"
    allowed_domains = ["indeed.com", "localhost"]
    start_urls = []
    date_scraped = datetime.now().strftime("%Y-%m-%d")
    proxy_username = '80c437873bbc27d63aa9'
    proxy_password = '60e5506f4a26d525'
    proxy_url = f'http://{proxy_username}:{proxy_password}@gw.dataimpulse.com:823'

    # Generar las URLs iniciales para cada palabra clave
    def __init__(self, *args, **kwargs):
        super(IndeedSpider, self).__init__(*args, **kwargs)
        keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo', 'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 'Vendedor', 'Promotor', 'Atencion']
        # keywords_jobs = ['Asistente']
        for keyword in keywords_jobs:
            self.start_urls.extend([f'https://pe.indeed.com/jobs?q={keyword}&l=Lima&sort=date&fromage=7&start={i}' for i in range(0, 10, 100)]) # Paginado de 10 en 10 (15 jobs por página)
            
    def start_requests(self):
        """
        Generates scrapy Requests for each URL in the start_urls list.
        
        Yields:
            SplashRequest: A scrapy Request object with SplashRequest parameters.
        """
        for url in self.start_urls:
            yield SplashRequest(url, self.parse, args={'wait': 2, 'proxy': self.proxy_url}, endpoint='render.html')
            # yield SplashRequest(url, self.parse, args={'wait': 5}, endpoint='render.html')

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
                item['date_scraped'] = self.date_scraped
                item['keyword'] = response.url.split('q=')[1].split('&')[0]  # Palabra clave utilizada para la búsqueda

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
            target_div = response.css('div.jobsearch-JobComponent-description')

            # Itera sobre los elementos dentro del target_div
            if target_div:
                for element in target_div.css('p, li'):
                    # Usa .css('::text') para obtener solo el texto dentro de los elementos
                    paragraph = element.css('::text').getall()
                    # Combina el texto y añade solo si no está vacío
                    cleaned_paragraph = ' '.join(paragraph).strip()
                    if cleaned_paragraph:
                        job_description_paragraphs.append(cleaned_paragraph)

            # Combina los párrafos en una sola cadena con dos saltos de línea
            job_description = '\n'.join(job_description_paragraphs)
            job_description = job_description.split('{flex:0 0 auto;min-width:0;}')[1]
            item['description'] = job_description
            
            # Obtiene el tipo de empleo
            type_of_job = response.css('div.js-match-insights-provider-1m98ica.e1xnxm2i0::attr(data-testid)').get()
            type_of_job = type_of_job.split('-')[0] if type_of_job else 'Tiempo completo'            
            # Verifica si type_of_job tiene un valor y es uno de los tipos esperados
            if type_of_job and type_of_job in ['Tiempo completo', 'Tiempo parcial', 'Por contrato', 'Indefinido', 'Temporal', 'Medio tiempo']:
                type_of_job = type_of_job.strip()  # Limpia el texto
            else:
                type_of_job = 'Tiempo completo'  # Valor por defecto si no coincide
                
            item['type_of_job'] = type_of_job
            
            # Guardar los datos en la base de datos
            self.save_pre_db(item) # Guarda el item sin usar GPT-3.5
    
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