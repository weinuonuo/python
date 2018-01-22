# -*- coding: utf-8 -*-
import re
import datetime
from datetime import timedelta
from scrapy.spider import CrawlSpider
from scrapy.selector import Selector
from scrapy.http import Request
from Sina_spider.items import InformationItem, TweetsItem, RelationshipsItem,CommentsItem,RepostsItem
import logging
from scrapy.shell import inspect_response
import urllib
import os
import json

class SinaspiderSpider(CrawlSpider):
    name = 'SinaSpider'
    host = "http://weibo.cn"
    weiboID = ['2286908003']
    start_urls = list(set(weiboID))
    logging.getLogger("requests").setLevel(logging.WARNING)  # 将requests的日志级别设成WARNING
    def start_requests(self):
        for uid in self.start_urls:
            yield Request(url="https://weibo.cn/%s/info" % uid, callback=self.parse_information)
    
    def parse_information(self, response):
        """ 抓取个人信息 """
        informationItem = InformationItem()
        selector = Selector(response)
        ID = re.findall('(\d+)/info', response.url)[0]
        try:
            logging.warning("开始解析个人信息...")
            # img_url = selector.xpath('//img[@alt="头像"]/@src').extract()
            # urllib.request.urlretrieve(img_url[0], './headimage/' + str(ID)+'.jpg')
            text1 = ";".join(selector.xpath('body/div[@class="c"]//text()').extract())  # 获取标签里的所有text()
            nickname = re.findall('昵称[;：:]+(.*?);', text1)
            gender = re.findall('性别[;：:]?(.*?);', text1)
            place = re.findall('地区[;：:]?(.*?);' , text1)
            briefIntroduction = re.findall('简介[;：:]?(.*?);' , text1)
            birthday = re.findall('生日[;：:]?(.*?);' , text1) 
            sexOrientation = re.findall('性取向[;：:]?(.*?);' , text1)
            sentiment = re.findall('感情状况[;：:]?(.*?);' , text1)
            vipLevel = re.findall('会员等级[;：:]?(.*?);' , text1)
            authentication = re.findall('认证[;：:]?(.*?);' , text1)
            url = re.findall('互联网[;：:]?(.*?);' , text1)
            logging.warning("解析完成...")
            informationItem["_id"] = ID
            # if img_url and img_url[0]:
            #     logging.warning("存入头像图片...")
            #     informationItem["img_url"] = img_url[0]
            if nickname and nickname[0]:
                logging.warning("存入姓名...")
                informationItem["NickName"] = nickname[0].replace(u"\xa0", "")
            if gender and gender[0]:
                logging.warning("存入性别...")
                informationItem["Gender"] = gender[0].replace(u"\xa0", "")
            if place and place[0]:
                logging.warning("存入地址...")
                place = place[0].replace(u"\xa0", "").split(" ")
                informationItem["Province"] = place[0]
                if len(place) > 1:
                    informationItem["City"] = place[1]
            if briefIntroduction and briefIntroduction[0]:
                logging.warning("存入简介...")
                informationItem["BriefIntroduction"] = briefIntroduction[0].replace(u"\xa0", "")
            if birthday and birthday[0]:
                logging.warning("存入生日...")
                try:
                    informationItem["Birthday"] = datetime.datetime.strptime(birthday[0], "%Y-%m-%d")
                except Exception:
                    informationItem['Birthday'] = birthday[0]   # 有可能是星座，而非时间
            if sexOrientation and sexOrientation[0]:
                logging.warning("存入性取向...")
                if sexOrientation[0].replace(u"\xa0", "") == gender[0]:
                    informationItem["SexOrientation"] = "同性恋"
                else:
                    informationItem["SexOrientation"] = "异性恋"
            if sentiment and sentiment[0]:
                logging.warning("存入情感状况...")
                informationItem["Sentiment"] = sentiment[0].replace(u"\xa0", "")
            if vipLevel and vipLevel[0]:
                logging.warning("存入会员等级...")
                informationItem["VIPlevel"] = vipLevel[0].replace(u"\xa0", "")
            if authentication and authentication[0]:
                logging.warning("存入认证...")
                informationItem["Authentication"] = authentication[0].replace(u"\xa0", "")
            if url:
                informationItem["URL"] = url[0]

            try:
                urlothers = "https://weibo.cn/attgroup/opening?uid=%s" % ID
                r = requests.get(urlothers, cookies=response.request.cookies, timeout=5)
                if r.status_code == 200:
                    selector = etree.HTML(r.content)
                    texts = ";".join(selector.xpath('//body//div[@class="tip2"]/a//text()'))
                    if texts:
                        logging.warning("开始解析微博数，关注数，粉丝数...")
                        num_tweets = re.findall('微博\[(\d+)\]', texts)
                        num_follows = re.findall('关注\[(\d+)\]', texts)
                        num_fans = re.findall('粉丝\[(\d+)\]', texts)
                        if num_tweets:
                            logging.warning("存入微博数...")
                            informationItem["Num_Tweets"] = int(num_tweets[0])
                        if num_follows:
                            logging.warning("存入关注数...")
                            informationItem["Num_Follows"] = int(num_follows[0])
                        if num_fans:
                            logging.warning("存入粉丝数...")
                            informationItem["Num_Fans"] = int(num_fans[0])
            except Exception :
                pass
        except Exception:
            logging.warning("未解析")
        else:
            yield informationItem
        yield Request(url="https://weibo.cn/%s/profile?filter=1&page=1" % ID, callback=self.parse_tweets, dont_filter=True)
        yield Request(url="https://weibo.cn/%s/follow" % ID, callback=self.parse_relationship, dont_filter=True)
        yield Request(url="https://weibo.cn/%s/fans" % ID, callback=self.parse_relationship, dont_filter=True)

    def parse_tweets(self, response):
        """ 抓取微博数据 """
        tweetIDs = []
        selector = Selector(response)
        ID = re.findall('(\d+)/profile', response.url)[0]
        divs = selector.xpath('body/div[@class="c" and @id]')
        for div in divs:
            try:
                logging.warning("开始解析微博数据...")
                tweetsItems = TweetsItem()
                id = div.xpath('@id').extract_first()[2:]  # 微博ID
                tweetIDs.append(id) # 加入微博列表
                content = div.xpath('div/span[@class="ctt"]//text()').extract()  # 微博内容
                cooridinates = div.xpath('div/a/@href').extract()  # 定位坐标
                like = re.findall('赞\[(\d+)\]', div.extract())  # 点赞数
                transfer = re.findall('转发\[(\d+)\]', div.extract())  # 转载数
                comment = re.findall('评论\[(\d+)\]', div.extract())  # 评论数
                others = div.xpath('div/span[@class="ct"]/text()').extract()  # 求时间和使用工具（手机或平台）
                tweetsItems["_id"] = ID + "-" + id
                tweetsItems["ID"] = ID
                if content:
                    logging.warning("存入微博内容...")
                    tweetsItems["Content"] = " ".join(content).strip('[位置]')  # 去掉最后的"[位置]"
                if cooridinates:
                    logging.warning("存入微博定位...")
                    cooridinates = re.findall('center=([\d.,]+)', cooridinates[0])
                    if cooridinates:
                        tweetsItems["Co_oridinates"] = cooridinates[0]
                if like:
                    logging.warning("存入点赞数...")
                    tweetsItems["Like"] = int(like[0])
                if transfer:
                    logging.warning("存入转发数...")
                    tweetsItems["Transfer"] = int(transfer[0])
                if comment:
                    logging.warning("存入评论数...")
                    tweetsItems["Comment"] = int(comment[0])
                if others:
                    others = others[0].split('来自')
                    pubtime = others[0].replace(u"\xa0", "")
                    if "分钟前" in pubtime: # 添加上年月日　计算时间
                        now = datetime.datetime.now()
                        time = re.findall("(\d+)分钟前",pubtime)
                        after = datetime.timedelta(minutes = int(time[0]))
                        tweetsItems["PubTime"] =  (now - after).strftime("%Y-%m-%d %H:%M:%S")
                    elif "今天" in pubtime: # 添加上年月日 加上时间
                        time = re.findall("今天 (.*)",pubtime)
                        now = datetime.datetime.now().strftime("%Y-%m-%d")
                        tweetsItems["PubTime"] =  now + " " +time[0]
                    elif re.search("20\d+\-",pubtime):
                        tweetsItems["PubTime"] = pubtime
                    else:                        # 只将格式转变为年月日格式
                        now = datetime.datetime.now().strftime("%Y")
                        try:
                            time = datetime.datetime.strptime(pubtime,"%m月%d日 %H:%M").strftime("%m-%d %H:%M")
                        except:
                            pass
                        else:
                            tweetsItems["PubTime"] =  now + "-" + time
                    if len(others) == 2:
                        tweetsItems["Tools"] = others[1].replace(u"\xa0", "")
            except Exception:
                pass
            else:
                yield tweetsItems

        for tweetID in tweetIDs:
            yield Request(url = "https://weibo.cn/comment/" + tweetID + "?&uid="+ ID +"&page=1",callback = self.parse_comments,dont_filter = True) # 抓取评论
            yield Request(url = "https://weibo.cn/repost/" + tweetID + "?&uid="+ ID +"&page=1",callback = self.parse_reposts,dont_filter = True) # 抓取转发

        url_next = selector.xpath('body/div[@class="pa" and @id="pagelist"]/form/div/a[text()="下页"]/@href').extract()
        if url_next:
            logging.warning(self.host + url_next[0])
            yield Request(url=self.host + url_next[0], callback=self.parse_tweets, dont_filter=True)

    def parse_comments(self,response):
        '''抓取评论'''
        selector = Selector(response)
        divs = selector.xpath('body/div[@class="c" and @id]')
        ID = re.findall('comment/([\w\d]+)\?\&uid=',response.url) # 微博ID
        for div in divs:
            try:
                user_id = div.xpath('a/@href').extract()
                user_name = div.xpath('a/text()').extract()
                likenum = re.findall('赞\[(\d+)\]',div.extract())
                source = re.findall('来自(.*?)</span>',div.extract())
                created_at = re.findall('<span class="ct">(.*?)\\xa0来自',div.extract())
                text = div.xpath('span[@class="ctt"]/text()').extract()
                commentItems = CommentsItem()
                if user_id and user_id[0]:
                    if len(user_id) == 2:
                        user_id = re.findall('&fuid=(\d+)',user_id[1])
                    commentItems["User_id"] = user_id[0]
                    commentItems['_id'] = ID[0] + "-" +user_id[0] # 主键
                if user_name and user_name[0]:
                    commentItems["User_name"] = user_name[0]
                if likenum and likenum[0]:
                    commentItems["Likenum"] = likenum[0]
                if source and source[0]:
                    if "iPhone客户端" in source[0]:
                        source[0] = "iPhone客户端"
                    commentItems["Source"] = source[0]
                if created_at and created_at[0]:
                    if "分钟前" in created_at[0]: # 添加上年月日　计算时间
                        now = datetime.datetime.now()
                        time = re.findall("(\d+)分钟前",created_at[0])
                        after = datetime.timedelta(minutes = int(time[0]))
                        commentItems["Created_at"] = (now - after).strftime("%Y-%m-%d %H:%M:%S")
                    elif "今天" in created_at[0]: # 添加上年月日 加上时间
                        time = re.findall("今天 (.*)",created_at[0])
                        now = datetime.datetime.now().strftime("%Y-%m-%d")
                        commentItems["Created_at"] = now + " " +time[0]
                    elif re.search("20\d+\-",created_at[0]):
                        commentItems["Created_at"] = created_at[0]
                    else:                        # 只将格式转变为年月日格式
                        now = datetime.datetime.now().strftime("%Y")
                        try:
                            time = datetime.datetime.strptime(created_at[0],"%m月%d日 %H:%M").strftime("%m-%d %H:%M")
                        except:
                            pass
                        else:
                            commentItems["Created_at"] =  now + "-" + time
                if text and text[0]:
                    if len(text) == 2 and text[0] == "回复":
                        name = div.xpath('span[@class="ctt"]/a/text()').extract()
                        if name and name[0]:
                            commentItems["Text"] = text[0] + name[0] + text[1]
                        else:
                            logging.warning("匹配不上")
                    else:
                        commentItems["Text"] = text[0]
            except Exception :
                logging.warning("评论爬取失败...")
                pass
            else:
                yield commentItems
        url_next = selector.xpath('body/div[@class="pa" and @id="pagelist"]/form/div/a[text()="下页"]/@href').extract()
        if url_next:
            logging.warning(self.host + url_next[0])
            yield Request(url = self.host + url_next[0],callback = self.parse_comments,dont_filter = True)

    def parse_reposts(self,response):
        '''抓取转发'''
        selector = Selector(response)
        divs = selector.xpath('body/div[@class="c"]')
        ID = re.findall('repost/([\w\d]+)\?\&uid=',response.url) # 微博ID
        for div in divs:
            try:
                # user_id = div.xpath('a/@href').extract()
                user_name = div.xpath('a/text()').extract()
                likenum = re.findall('赞\[(\d+)\]',div.extract())
                source = re.findall('来自(.*?)</span>',div.extract())
                created_at = re.findall('<span class="ct">\\xa0(.*?)\\xa0来自',div.extract())
                text = re.findall('\:(.*?)\\xa0\<span class=\"cc\"\>',div.extract())
                repostsItems = RepostsItem()
                repostsItems['_id'] = ID[0] + "-" + user_name[0]
                # if user_id and user_id[0]:
                #     if len(user_id) == 2:
                #         user_id = re.findall('&fuid=(\d+)',user_id[1])
                #     repostsItems["User_id"] = User_id[0]
                if user_name and user_name[0] != '返回我的首页':
                    repostsItems["User_name"] = user_name[0]
                if likenum and likenum[0]:
                    repostsItems["Likenum"] = likenum[0]
                if source and source[0]:
                    repostsItems["Source"] = source[0]
                if created_at and created_at[0]:
                    if "分钟前" in created_at[0]: # 添加上年月日　计算时间
                        now = datetime.datetime.now()
                        time = re.findall("(\d+)分钟前",created_at[0])
                        after = datetime.timedelta(minutes = int(time[0]))
                        repostsItems["Created_at"] = (now - after).strftime("%Y-%m-%d %H:%M:%S")
                    elif "今天" in created_at[0]: # 添加上年月日 加上时间
                        time = re.findall("今天 (.*)",created_at[0])
                        now = datetime.datetime.now().strftime("%Y-%m-%d")
                        repostsItems["Created_at"] = now + " " +time[0]
                    elif re.search("20\d+\-",created_at[0]):
                        repostsItems["Created_at"] = created_at[0]
                    else:                        # 只将格式转变为年月日格式
                        now = datetime.datetime.now().strftime("%Y")
                        try:
                            time = datetime.datetime.strptime(created_at[0],"%m月%d日 %H:%M").strftime("%m-%d %H:%M")
                        except:
                            pass
                        else:
                            repostsItems["Created_at"] =  now + "-" + time
                if text and text[0]:
                    repost_text = re.split("<|>",text[0])
                    line = ""
                    for i in repost_text:
                        if "alt=" not in i and "a href" not in i and "/a" not in i:
                            line = line + " " + i    
                    repostsItems["Text"] = line
            except Exception :
                logging.warning("转发爬取失败...")
                pass
            else:
                yield repostsItems
                
        url_next = selector.xpath('body/div[@class="pa" and @id="pagelist"]/form/div/a[text()="下页"]/@href').extract()
        if url_next:
            logging.warning(self.host + url_next[0])
            yield Request(url = self.host + url_next[0],callback = self.parse_reposts,dont_filter = True)
    
    def parse_relationship(self, response):
        """ 打开url爬取里面的个人ID """
        selector = Selector(response)
        if "/follow" in response.url:
            ID = re.findall('(\d+)/follow', response.url)[0]
            flag = True
        else:
            ID = re.findall('(\d+)/fans', response.url)[0]
            flag = False 
        urls = selector.xpath('//a[text()="关注他" or text()="关注她"]/@href').extract()
        uids = re.findall('uid=(\d+)', ";".join(urls), re.S)
        for uid in uids:
            relationshipsItem = RelationshipsItem()
            relationshipsItem["Host1"] = ID if flag else uid
            relationshipsItem["Host2"] = uid if flag else ID
            yield relationshipsItem
            yield Request(url="https://weibo.cn/%s/info" % uid, callback=self.parse_information)

        next_url = selector.xpath('//a[text()="下页"]/@href').extract()
        if next_url:
            yield Request(url=self.host + next_url[0], callback=self.parse_relationship, dont_filter=True)

    