# from lxml import etree
# import urllib.request
# -*- coding: utf-8 -*-
import scrapy
# import re
import pymysql
import random
from scrapy import selector, Request
import logging
import datetime
import time
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.action_chains import ActionChains as AC
from save_action.items import *
import requests
import json


class SaveActionSpiderSpider(scrapy.Spider):
    name = 'save_action_spider'
    allowed_domains = ['www.liveauctioneers.com','item-api-prod.liveauctioneers.com']
    start_urls = ['http://www.liveauctioneers.com/']
    
    item_info_base='https://www.liveauctioneers.com/item/{item_id}'
    login_url='https://item-api-prod.liveauctioneers.com/auth/spalogin?c=20170802'
    save_url='https://item-api-prod.liveauctioneers.com/saved-items/save/{item_id}?c=20170802'


    utc_datetime=datetime.datetime.utcnow()
    utc_today_str=utc_datetime.strftime('%Y-%m-%d')
    # logging.basicConfig(filename='scarpy_{}.log'.format(utc_today_str))

    def __init__(self, start_account_number=1,end_account_number=10, *args, **kwargs):
        super(SaveActionSpiderSpider, self).__init__(*args, **kwargs)
        self.start_account_number=int(start_account_number)
        self.end_account_number=int(end_account_number)

    def parse_saveAndFollowToday(self,response):
            """
            save操作与跟踪bidding信息
            """
            #对今天开始操作
            try:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='连接数据库'))
                db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
                cursor=db.cursor()
                sql_need_to_be_saved='SELECT item_id FROM items_info WHERE save_action_date=date_format("{date}","%Y-%m-%d")  AND experiment_type=1;'.format(date=self.utc_today_str)
                cursor.execute(sql_need_to_be_saved)
                item_need_to_be_save=[]
                items=cursor.fetchall()
                if items:
                    for item in items:
                        logging.info('----------------------------------------{info}----------------------------------------'.format(info='待保存：'+str(item[0])))
                        item_need_to_be_save.append(int(item[0]))
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='待判定：'+str(len(item_need_to_be_save))))
                else:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='没有要保存的item'))
                    
                db.close()

                for i in range(self.start_account_number,self.end_account_number+1):
                # i=self.account_number
                    headers=self.settings.get('HEADERS')
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始登陆账号'+str(i)))
                    login_info={}
                    login_info["password"]=
                    login_info["username"]=
                    login_response=requests.post(self.login_url,json=login_info,headers=headers)

                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='设置token'))
                    login_json=json.loads(login_response.text)
                    token=login_json.get("data").get("token")
                    headers["Authorization"]="Bearer {}".format(token)

                    for j in range(len(item_need_to_be_save)):
                        logging.info('----------------------------------------{info}----------------------------------------'.format(info='账号'+str(i)+'的保存item操作'))
                        item_id=item_need_to_be_save[j]
                        if  random.randint(0,1):    
                            logging.info('----------------------------------------{info}----------------------------------------'.format(info='决定保存：'+str(item_id)))
                            savecode=0

                            # 执行操作
                            try:
                                save_info={"itemId":item_id}
                                save_response=requests.post(self.save_url.format(item_id=str(item_id)),json=save_info,headers=headers)
                                if save_response.status_code==200:
                                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='成功保存：'+str(item_id)))
                                    savecode=5
                            except:
                                logging.info('----------------------------------------{info}----------------------------------------'.format(info='保存失败：'+str(item_id)))
                                savecode=6

                            #保存记录
                            logging.info('----------------------------------------{info}----------------------------------------'.format(info='save_item记录进入数据库'))
                            accounts_saved_info=Liveauctioneers_AccountsSavedInfo()
                            accounts_saved_info['account_id']=i
                            accounts_saved_info['item_id']=item_id
                            accounts_saved_info['record_date']=self.utc_today_str
                            accounts_saved_info['record_time']=datetime.datetime.utcnow().strftime('%H:%M:%S')
                            accounts_saved_info['save_code']=savecode

                            yield accounts_saved_info
                            logging.info('----------------------------------------{info}----------------------------------------'.format(info='保存操作完成：'+str(item_id)))
                        else:
                            logging.info('----------------------------------------{info}----------------------------------------'.format(info='不决定保存该item'))

            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='抓取中有其他错误'))


    def start_requests(self):
        """
        请求开始
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info=self.utc_today_str+':爬虫开始运行(UTC时间)'))

        try:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始保存操作与抓过去item拍卖次数'))
            yield Request(url='https://www.liveauctioneers.com',callback=self.parse_saveAndFollowToday,priority=1,headers=self.settings.get('HEADERS'))
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='保存或者抓取中有错'))
