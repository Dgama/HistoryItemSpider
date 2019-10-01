# -*- coding: utf-8 -*-
import scrapy
import pymysql
import threading
import datetime
import logging
from scrapy import Request,FormRequest
from new_spider.items import *
import requests
import json
import re



class NewspiderSpider(scrapy.Spider):
    name = 'newspider'
    start_urls = ['http://www.liveauctioneers.com/']

    allowed_domains = ['classic.liveauctioneers.com','www.liveauctioneers.com','item-api-prod.liveauctioneers.com','p1.liveauctioneers.com']
    first_page='https://www.liveauctioneers.com/c/{category}/?page={page}&pageSize={rows}&sort={sort}'
    item_info_base='https://www.liveauctioneers.com/item/{item_id}'
    bidding_info_base='https://item-api-prod.liveauctioneers.com/spa/small/item/{item_id}/bidding?c=20170802'
    item_watching_info_base='https://item-api-prod.liveauctioneers.com/saved-items/count?c=20170802'
    follower_url='https://item-api-prod.liveauctioneers.com/follower-count/?c=20170802'

    #UTC时间：
    utc_datetime=datetime.datetime.utcnow()
    utc_today_str=utc_datetime.strftime('%Y-%m-%d')

    item_id_pattern=re.compile('/item/(.*?)_.*')

    def __init__(self, follow_start_date=0,follow_end_date=11, restart_item_id=0,function_type=0,*args, **kwargs):
        super(NewspiderSpider, self).__init__(*args, **kwargs)
        self.follow_start_date=follow_start_date
        self.follow_end_date=follow_end_date
        self.function_type=int(function_type)
        self.restart_item_id=int(restart_item_id)
    
    def parse_followerInfo(self,response):
        follower_list=response.meta.get('follower_list')
        for i in range(0,len(follower_list)):
            auctioneer_id=follower_list[i]
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='商家:{}'.format(str(auctioneer_id))))
            post_data={"sellerIds":[auctioneer_id]}
            response=requests.post(self.follower_url,json=post_data)
            try:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='保存商家{}粉丝信息获取成功'.format(str(auctioneer_id))))
                r_json=json.loads(response.text)
                auctioneer_followers=Liveauctioneers_AuctioneersFollowers()
                auctioneer_followers['auctioneer_id']=auctioneer_id
                auctioneer_followers['followers']=r_json.get('data')[0].get(str(auctioneer_id))
                auctioneer_followers['record_date']=self.utc_today_str
                auctioneer_followers['record_time']=datetime.datetime.utcnow().strftime('%H:%M:%S')
                yield auctioneer_followers
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='商家{}粉丝信息保存完成'.format(str(auctioneer_id))))
            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='拍卖商粉丝信息有误'))
    
    def parse_itembiddinginfo(self,response):
        """
        解析商品当日交易信息
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取item：'+str(response.meta.get("item_id"))+'的bidding信息'))
        try:
            item_bidding_info=Liveauctionners_item_bidding_overview()
            #获取watching人数
            post_data={"ids":[response.meta.get('item_id')]}
            r=requests.post('https://item-api-prod.liveauctioneers.com/saved-items/count?c=20170802',json=post_data)
            r_json=json.loads(r.text)
            item_bidding_info['bidders_watching']=r_json.get('data').get('savedItemCounts')[0].get('savedCount')

            item_bidding_info['record_date']=self.utc_today_str
            item_bidding_info['record_time']=datetime.datetime.utcnow().strftime('%H:%M:%S')

            #获取其他字段
            result=json.loads(response.text)
            field_map={'item_id':'itemId','bids_now':'bidCount','whether_sold':'isSold','sold_price':'salePrice','leading_bid':'leadingBid'}
            for field, attr in field_map.items():
                item_bidding_info[field]=result.get('data')[0].get(attr)
            try:
                #如果已经成交则单独记录成交信息
                if result.get('data')[0].get('isSold')==True:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='商品已经成交,记录每次拍卖详情'))
                    yield Request(self.item_info_base.format(item_id=response.meta.get('item_id')),callback=self.parse_auctioninfo,headers=self.settings.get('HEADERS'),meta={'item_id':response.meta.get('item_id')})
                
                yield item_bidding_info
            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='商品成交信息出错'))
                yield item_bidding_info
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='商品bidding信息获取有误'))

    def parse_auctioninfo(self,response):
        """
        爬取具体交易信息
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='记录已经成交商品：'+str(response.meta.get("item_id"))+'信息'))
        try:
            pattern=re.compile('"amount":(.*?),"bidderId":(.*?),"currency":"(.*?)","source":"(.*?)"')
            results=re.findall(pattern,response.text)
            number_of_results=len(results)
            item_id=response.meta.get("item_id")
            for result in results:
                item_auction_info=Liveauctioneers_ItemAuctionInfo()
                item_auction_info["item_id"]=item_id
                item_auction_info["bidding_number"]=number_of_results
                item_auction_info["bidding_type"]=result[3]
                item_auction_info["bidding_price"]=result[0]
                item_auction_info["bidding_currency"]=result[2]
                item_auction_info["bidder_id"]=result[1]
                number_of_results-=1
                yield item_auction_info
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='成交信息获取失败'))

    def parse_itemLocation(self,response):

        page=response.meta.get('page')

        db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))

        cursor=db.cursor()
        lock=threading.Lock()

        dividors=response.xpath('//div[@class="card___1ZynM cards___2C_7Z"]')
        if dividors:
            for i in range(1,len(dividors)+1):
                href=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][{num}]//a[@class="link___ link-primary___ item-title___24bKg"]/@href)'.format(num=i)).extract()[0]
                if href:
                    item_id=int(re.search(self.item_id_pattern,href).group(1))
                else:
                    item_id='0'
                
                sql_item='SELECT record_date FROM items_info WHERE item_id={item_id};'.format(item_id=item_id)

                lock.acquire()
                cursor.execute(sql_item)
                item=cursor.fetchone()
                lock.release()

                if item:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info=str(item_id)+'在第'+str(page)+'的'+str(i)+'中'))
                    item_location=Liveauctioneers_itemsLocation()
                    item_location['item_id']=item_id
                    item_location['page']=page
                    item_location['record_date']=self.utc_today_str
                    item_location['record_time']=datetime.datetime.utcnow().strftime('%H%M%S')
                    item_location['location']=i
                    yield item_location
                else:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='没有发现item'+str(item_id)))
            
        if page<5:
            yield Request(self.first_page.format(category=response.meta.get('category'),sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=page+1),
            callback=self.parse_itemLocation,
            headers=self.settings.get('HEADERS'),
            meta={'category':response.meta.get('category'),'sort':'dateasc','rows':self.settings.get('ROWS'),'page':page+1})

        db.close()

    def start_requests(self):

        db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
        try: 
            db.ping()
        except:
            db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
        cursor=db.cursor()
        lock=threading.Lock()
        
        if self.function_type==0 or self.function_type==1:
            try:
                # 生成持续跟踪物品信息爬取
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='抓取历史item每日bidding信息'))
                sql_follow_today='SELECT item_id FROM items_info WHERE date_add(record_date, INTERVAL {end} day)>=date_format("{date}","%Y-%m-%d") AND date_add(record_date, INTERVAL {start} day)<=date_format("{date}","%Y-%m-%d") AND item_id>={restart} ORDER BY item_id;'.format(date=self.utc_today_str,start=self.follow_start_date,end=self.follow_end_date,restart=self.restart_item_id)

                lock.acquire()
                cursor.execute(sql_follow_today)
                lock.release()

                item_set=[]
                
                items_follow_today=cursor.fetchall()
                if items_follow_today:
                    for item in items_follow_today:
                        item_set.append(item[0])
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='从'+str(item_set[0])+'到'+str(item_set[-1])+'共'+str(len(item_set))+'个'))
                    for item in item_set:
                        yield Request(self.bidding_info_base.format(item_id=item),callback=self.parse_itembiddinginfo,meta={'item_id':item})
                            # yield Request(self.item_watching_info_base,method='POST',body={"ids":'['+str(item_id)+']'},callback=self.parse_try)

                else:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='没有需要抓取历史item每日bidding信息'))
            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='保存信息出错'))

        if self.function_type==0 or self.function_type==2:
            try: 
                db.ping() 
            except:
                db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
            
            try:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始记录商家粉丝数量'))
                sql_followers_today='SELECT auctioneer_id FROM auctioneers_info'

                lock.acquire()
                cursor.execute(sql_followers_today)
                lock.release()

                followers_today=cursor.fetchall()
                if followers_today:
                    follower_list=[]
                    for follow in followers_today:
                        follower_list.append(int(follow[0]))
                    yield Request(self.first_page,callback=self.parse_followerInfo,meta={'follower_list':follower_list},headers=self.settings.get('HEADERS'))
            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='记录粉丝信息出错'))
        db.close()

        if self.function_type==0 or self.function_type==3:
            for i in range(0,len(self.settings.get('CATEGORIES'))):
                # 获取当日新数据
                category=self.settings.get('CATEGORIES')[i]
                #抓取前五页item并比对
                try:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取前'+category+'5页item'))
                    yield Request(self.first_page.format(category=category,sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=1),
                    callback=self.parse_itemLocation,
                    headers=self.settings.get('HEADERS'),
                    meta={'category':category,'sort':'dateasc','rows':self.settings.get('ROWS'),'page':1})
                except:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取'+category+'前5页数据有错'))
