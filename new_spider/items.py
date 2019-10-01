# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field,Item


class  Liveauctionners_item_bidding_overview(scrapy.Item):
    """
    产品交易信息概览
    """
    table='items_bidding_overview'
    item_id= Field()
    record_date=Field()
    record_time=Field()
    bids_now=Field()
    bidders_watching=Field()
    sold_price=Field()
    whether_sold=Field()
    leading_bid=Field()

class Liveauctioneers_ItemAuctionInfo(scrapy.Item):
    """
   成交 交易信息
    """
    table='items_auctioninfo'
    item_id=Field()
    bidding_number=Field()
    bidding_type=Field()
    bidding_price=Field()
    bidding_currency=Field()
    bidder_id=Field()

class Liveauctioneers_itemsLocation(scrapy.Item):
    """
    产品位于1-5页的哪一页
    """
    table='items_location'
    item_id=Field()
    page=Field()
    record_date=Field()
    record_time=Field()
    location=Field()

class Liveauctioneers_AuctioneersFollowers(scrapy.Item):
    """
    动态粉丝数量
    """
    table='auctioneers_followers'
    auctioneer_id= Field()
    followers= Field()
    record_date= Field()
    record_time=Field()
