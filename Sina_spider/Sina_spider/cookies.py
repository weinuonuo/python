import base64
import requests
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import logging
from . import user_agents
import rsa
import math
import random
import binascii
import re
from urllib.parse import quote_plus

IDENTIFY = 1  # 验证码输入方式:        1:看截图aa.png，手动输入     2:云打码
COOKIE_GETWAY = 0 # 0 代表从https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18) 获取cookie   # 1 代表从https://weibo.cn/login/获取Cookie
dcap = dict(DesiredCapabilities.PHANTOMJS)  # PhantomJS需要使用老版手机的user-agent，不然验证码会无法通过
dcap["phantomjs.page.settings.userAgent"] = (
    "Mozilla/5.0 (Linux; U; Android 2.3.6; en-us; Nexus S Build/GRK39F) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"
)
logger = logging.getLogger(__name__)
logging.getLogger("selenium").setLevel(logging.WARNING)  # 将selenium的日志级别设成WARNING，太烦人

myWeiBo = [
    {'no':'956902681@qq.com','psw':'123qwe!@#'},
    {'no':'shixiaotian147@sina.com','psw':'xiaoxiao512'}
]

def getCookie(account, password):
    if COOKIE_GETWAY == 0:
        return get_cookie_from_login_sina_com_cn(account, password)
    else:
        logger.error("COOKIE_GETWAY Error!")

def get_cookie_from_login_sina_com_cn(username, password):
    """ 获取一个账号的Cookie """
    agent = random.choice(user_agents.agents)
    headers = {'User-Agent': agent}

    session = requests.session()
    def get_pincode_url(pcid):
        size = 0
        url = "http://login.sina.com.cn/cgi/pin.php"
        pincode_url = '{}?r={}&s={}&p={}'.format(url, math.floor(random.random() * 100000000), size, pcid)
        return pincode_url

    def get_su(username):
        """
        对 email 地址和手机号码 先 javascript 中 encodeURIComponent
        对应 Python 3 中的是 urllib.parse.quote_plus
        然后在 base64 加密后decode
        """
        username_quote = quote_plus(username)
        username_base64 = base64.b64encode(username_quote.encode("utf-8"))
        return username_base64.decode("utf-8")


    # 预登陆获得 servertime, nonce, pubkey, rsakv
    def get_server_data(su):
        pre_url = "http://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su="
        pre_url = pre_url + su + "&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.18)&_="
        prelogin_url = pre_url + str(int(time.time() * 1000))
        pre_data_res = session.get(prelogin_url, headers=headers)

        sever_data = eval(pre_data_res.content.decode("utf-8").replace("sinaSSOController.preloginCallBack", ''))

        return sever_data


    # 这一段用户加密密码，需要参考加密文件
    def get_password(password, servertime, nonce, pubkey):
        rsaPublickey = int(pubkey, 16)
        key = rsa.PublicKey(rsaPublickey, 65537)  # 创建公钥,
        message = str(servertime) + '\t' + str(nonce) + '\n' + str(password)  # 拼接明文js加密文件中得到
        message = message.encode("utf-8")
        passwd = rsa.encrypt(message, key)  # 加密
        passwd = binascii.b2a_hex(passwd)  # 将加密信息转换为16进制。
        return passwd


    # su 是加密后的用户名
    su = get_su(username)
    sever_data = get_server_data(su)
    servertime = sever_data["servertime"]
    nonce = sever_data['nonce']
    rsakv = sever_data["rsakv"]
    pubkey = sever_data["pubkey"]
    password_secret = get_password(password, servertime, nonce, pubkey)

    postdata = {
        'entry': 'weibo',
        'gateway': '1',
        'from': '',
        'savestate': '7',
        'useticket': '1',
        'pagerefer': "http://login.sina.com.cn/sso/logout.php?entry=miniblog&r=http%3A%2F%2Fweibo.com%2Flogout.php%3Fbackurl",
        'vsnf': '1',
        'su': su,
        'service': 'miniblog',
        'servertime': servertime,
        'nonce': nonce,
        'pwencode': 'rsa2',
        'rsakv': rsakv,
        'sp': password_secret,
        'sr': '1366*768',
        'encoding': 'UTF-8',
        'prelt': '115',
        'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack',
        'returntype': 'META'
        }
    need_pin = sever_data['showpin']
    if need_pin == 1:
        print("需要验证码")
        return ""
    
    login_url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)'
    login_page = session.post(login_url, data=postdata, headers=headers)
    login_loop = (login_page.content.decode("GBK"))
    pa = r'location\.replace\([\'"](.*?)[\'"]\)'
    loop_url = re.findall(pa, login_loop)[0]
    login_index = session.get(loop_url, headers=headers)
    uuid = login_index.text
    uuid_pa = r'"uniqueid":"(.*?)"'
    uuid_res = re.findall(uuid_pa, uuid, re.S)[0]
    web_weibo_url = "http://weibo.com/%s/profile?topnav=1&wvr=6&is_all=1" % uuid_res
    weibo_page = session.get(web_weibo_url, headers=headers)
    weibo_pa = r'<title>(.*?)</title>'
    user_name = re.findall(weibo_pa, weibo_page.content.decode("utf-8", 'ignore'), re.S)[0]
    print('登陆成功，你的用户名为：'+user_name)
    return session.cookies.get_dict()
    

def getCookies(weibo):
    """ 获取Cookies """
    cookies = []
    for elem in weibo:
        account = elem['no']
        password = elem['psw']
        cookie  =  getCookie(account, password)
        if cookie != None:
            cookies.append(cookie)

    return cookies


# cookies = getCookies(myWeiBo)
# cookie_str = input(print("请输入cookies")).split(";")
# for cookie_split in cookie_str:
#     cook = cookie_split.split(":")
cookies = [{"SCF":"AowFceI_zzoQ_h3OwAH2_Wmnnj_YaF5nNBU3FKzfKEaJWLdPGbtefigBTcX59ots2yYgByKdHJNJoLpnbBjeWYs.", "SUBP":"0033WrSXqPxfM725Ws9jqgMF55529P9D9W5jwTHV1uKX.I0DBUD3s24_5JpX5KMhUgL.Foz01KB71h-41Ke2dJLoI7LkHgfyMcvfMfYt", "_T_WM":"d45672dfe40f0de497957364acd5ca71", "SUB":"_2A253WC7JDeThGeRN4lYR-CvFwj-IHXVUorKBrDV6PUJbkdAKLVn7kW1NU2M5rCPdH8eZR2prvCPEUS_lerw6O-Tk", "SUHB":"0FQ64uhw9m8H8h","SSOLoginState":"1516002969", "M_WEIBOCN_PARAMS":"uicode%3D20000174%26featurecode%3D20000320%26fid%3Dhotword"}]
# logger.warning("Get Cookies Finish!( Num:%d)" % len(cookies))