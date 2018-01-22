# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo
from . import items
import logging


class MongoDBPipleline(object):
    
    def __init__(self):
        clinet = pymongo.MongoClient("localhost", 27017)
        db = clinet["Sina"]
        self.Information = db["Information"]
        self.Tweets = db["Tweets"]
        self.Relationships = db["Relationships"]
        self.Comments = db["Comments"]
        self.Reposts = db['Reposts']
    
    def process_item(self, item, spider):
        """ 判断item的类型，并作相应的处理，再入数据库 """
        if isinstance(item, items.InformationItem):
            try:
                logging.warning("向数据库存入个人信息...")
                self.Information.insert(dict(item))
            except Exception:
                logging.warning("数据已存在，存入个人信息失败/(ㄒoㄒ)/~~")
                pass
        elif isinstance(item, items.TweetsItem):
            try:
                logging.warning("向数据库存入微博信息...")
                self.Tweets.insert(dict(item))
            except Exception:
                logging.warning("数据已存在，存入微博信息数据失败/(ㄒoㄒ)/~~")
                pass
        elif isinstance(item, items.RelationshipsItem):
            try:
                logging.warning("向数据库存入关系数据信息...")
                self.Relationships.insert(dict(item))
            except Exception:
                logging.warning("数据已存在，存入两者关系数据失败/(ㄒoㄒ)/~~")
                pass
        elif isinstance(item,items.CommentsItem):
            try:
                logging.warning("向数据库存入微博评论信息...")
                self.Comments.insert(dict(item))
            except Exception:
                logging.warning("数据已存在，存入数据库失败...")
                pass
        elif isinstance(item,items.RepostsItem):
            try:
                logging.warning("向数据库存入微博转发信息...")
                self.Reposts.insert(dict(item))
            except Exception:
                logging.warning("数据已存在，存入数据库失败...")
                pass
        return item

# class MyImagesPipeline(ImagesPipeline):
#     def file_path(self, request, response=None, info=None):
#         image_guid = request.url.split('/')[-1]
#         return 'full/%s' % (image_guid)

#     def get_media_requests(self, item, info):
#         if isinstance(item, items.InformationItem):
#             for image_url in item['img_url']:
#                 yield Request(image_url)

#     def item_completed(self, results, item, info):
#         image_paths = [x['path'] for ok, x in results if ok]
#         if not image_paths:
#             raise DropItem("Item contains no images")
#         return item