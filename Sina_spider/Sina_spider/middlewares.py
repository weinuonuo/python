# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
import random
from . import user_agents
from . import cookies



class UserAgentMiddleware(object):
    """ 换User-Agent """

    def process_request(self, request, spider):
        agent = random.choice(user_agents.agents)
        request.headers["User-Agent"] = agent


class CookiesMiddleware(object):
    """ 换Cookie """

    def process_request(self, request, spider):
        cookie = random.choice(cookies.cookies)
        request.cookies = cookie
