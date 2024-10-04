import scrapy
from datetime import datetime, timedelta
from job_scraper.items import JobItem  # Asegúrate de que el JobItem esté definido en items.py
from job_scraper.utils.sql_alchemy import Job, SessionLocal  # Asegúrate de que esté bien configurado
from job_scraper.utils.sql_alchemy_pre_db import PreJob
from sqlalchemy.exc import SQLAlchemyError
from job_scraper.utils.langchain_descript_extraction import get_keywords # Importa la función OpenAI Api
import traceback

class ComputrabajoSpider(scrapy.Spider):
    name = "computrabajo_spider"
    allowed_domains = ["computrabajo.com.pe", "pe.computrabajo.com", "httpbin.org"]
    start_urls = []
    date_scraped = datetime.now().strftime("%Y-%m-%d")
    proxy_username = '80c437873bbc27d63aa9'
    proxy_password = '60e5506f4a26d525'
    proxy_url = f'http://{proxy_username}:{proxy_password}@gw.dataimpulse.com:823'

    # Generar las URLs iniciales para cada palabra clave
    def __init__(self, *args, **kwargs):
        super(ComputrabajoSpider, self).__init__(*args, **kwargs)
        keywords_jobs = ['Asistente', 'Practicante', 'Asesor', 'Auxiliar', 'Analista', 'Tecnico', 'Ejecutivo', 'Diseñador', 'Representante', 'Desarrollador', 'Coordinador', 'Soporte', 'Jefe', 'Vendedor', 'Promotor', 'Atencion']
        # keywords_jobs = ['Asistente']
        for keyword in keywords_jobs:
            self.start_urls.extend([f'https://pe.computrabajo.com/trabajo-de-{keyword}?by=publicationtime&pubdate=7&p={i}' for i in range(1, 20)]) # 20 jobs por página
            
    def start_requests(self):
        # Check IP before setting proxy
        yield scrapy.Request('http://httpbin.org/ip', callback=self.check_ip, meta={'proxy': None, 'check': 'before'})
        
        # for url in self.start_urls:
        #     yield scrapy.Request(url, callback=self.parse, meta={'proxy': self.proxy_url})
            
    def check_ip(self, response):
        ip = response.json().get('origin')
        check = response.meta.get('check')
        self.log(f"IP {check}: {ip}")
        self.log(f"IP {check}: {ip}")
        self.log(f"IP {check}: {ip}")
        self.log(f"IP {check}: {ip}")
        self.log(f"IP {check}: {ip}")

        # Check IP after setting proxy
        if check == 'before':
            # Agregar un parámetro de consulta único
            yield scrapy.Request('http://httpbin.org/ip?check=after', callback=self.check_ip, meta={'proxy': self.proxy_url, 'check': 'after'})
        else:
            for url in self.start_urls:
                yield scrapy.Request(url, callback=self.parse, meta={'proxy': self.proxy_url})

    def parse(self, response):      
        """
        Parse method for the spider. Extracts company, title, location, date, and job description URL from the response.
        Args:
            response (scrapy.http.Response): The response object containing the web page data.
        Yields:
            scrapy.Request: A request object to scrape the job description page.
        Returns:
            None
        """
        
        # Encuentra los elementos de la empresa, título, ubicación y fecha
        company_elements = response.xpath("//p[@class='dIB fs16 fc_base mt5']/a[@class='fc_base t_ellipsis']")
        title_elements = response.xpath("//h2[@class='fs18 fwB']/a[@class='js-o-link fc_base']")
        location_elements = response.xpath("//p[@class='fs16 fc_base mt5']/span[@class='mr10']")
        date_elements = response.xpath("//p[@class='fs13 fc_aux mt15']")

        if not company_elements or not title_elements or not location_elements or not date_elements:
            self.log("No more jobs found, ending pagination.")
            return
        
        for job in range(min(len(company_elements), len(title_elements), len(location_elements), len(date_elements))):
            item = JobItem()
            try:
                # Obtiene el nombre de la empresa
                item['company'] = company_elements[job].xpath(".//text()").get().strip()
                self.log(f"Company: {item['company']}")
                
                # Obtiene el título del empleo
                item['title'] = title_elements[job].xpath(".//text()").get().strip()
                self.log(f"Title: {item['title']}")
                
                # Obtiene la ubicación del empleo
                item['location'] = location_elements[job].xpath(".//text()").get().strip()
                self.log(f"Location: {item['location']}")
                
                # Obtiene la fecha de publicación del empleo
                job_date_text = date_elements[job].xpath(".//text()").get().strip()
                item['date'] = self.convert_to_date(job_date_text)
                self.log(f"Date: {item['date']}")
                
                # Obtiene la URL de la descripción del empleo
                job_description_href = title_elements[job].xpath(".//@href").get()
                item['link_url'] = response.urljoin(job_description_href)
                print(f"Link: {item['link_url']}")
                
                item['platform'] = 'Computrabajo'
                item['date_scraped'] = self.date_scraped
                item['keyword'] = response.url.split('/')[-1].split('-')[-1].split('?')[0]
                
                # Realizar una solicitud para obtener la descripción del empleo
                yield scrapy.Request(
                    url=item['link_url'],
                    callback=self.parse_job_description,
                    meta={'item': item},
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
            # Obtiene la descripción del empleo
            job_description = response.xpath("//div[@class='mb40 pb40 bb1'][@div-link='oferta']//p[@class='mbB']/text()").getall()
            job_description = "\n".join(job_description).strip() if job_description else ''
            item['description'] = job_description
                  
            # Obtiene el tipo de empleo
            type_of_job = response.xpath("//div[@class='mb40 pb40 bb1'][@div-link='oferta']//div[@class='mbB']//span[@class='tag base mb10'][3]/text()").get()
            type_of_job = type_of_job.strip() if type_of_job else 'N/A'
            item['type_of_job'] = type_of_job

            # Guardar los datos en la base de datos
            self.save_pre_db(item)
        
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
                platform=item['platform'],
                description=item['description'],
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
        >>> convert_to_date('ayer')
        datetime.datetime(2022, 1, 1, 0, 0)

        >>> convert_to_date('2 días')
        datetime.datetime(2021, 12, 30, 0, 0)
        """
        today = datetime.now()
        if 'ayer' in date_text.lower():
            return today - timedelta(days=1)
        elif 'hora' in date_text.lower():
            hours = int(date_text.split()[1])
            return today - timedelta(hours=hours)
        elif 'día' in date_text or 'días' in date_text:
            days = int(date_text.split()[1])
            return today - timedelta(days=days)
        else:
            return today
