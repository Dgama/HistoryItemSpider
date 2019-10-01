# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Item,Field


class Liveauctioneers_AccountsSavedInfo(scrapy.Item):
    """
    记录每个账号参与的每个save操作
    """
    table='accounts_saved_info'
    account_id=Field()
    item_id=Field()
    record_date=Field()
    record_time=Field()
    save_code=Field()

