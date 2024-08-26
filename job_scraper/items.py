# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class JobItem(scrapy.Item):
    company = scrapy.Field()
    title = scrapy.Field()
    location = scrapy.Field()
    date = scrapy.Field()
    platform = scrapy.Field()
    link_url = scrapy.Field()
    date_scraped = scrapy.Field()
    soft_skills = scrapy.Field()
    hard_skills = scrapy.Field()
    education = scrapy.Field()
    careers = scrapy.Field()
    seniority = scrapy.Field()
    type_of_job = scrapy.Field()
    work_mode = scrapy.Field()
    lgtbq = scrapy.Field()
    keyword = scrapy.Field()
    state = scrapy.Field()
