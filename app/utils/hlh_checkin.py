#!/usr/bin/python3.7
# -*- coding: utf-8 -*-
# @Time    : 2023/8/3 15:09
# @Author  : lxm
# @File    : hlh_checkin.py


import time
import requests
from loguru import logger

class hlh:

    def __init__(self, OPENID: str, **kwargs):
        self.openid = OPENID


    def get_cookie(self):
        url_login = r'https://sjzhlh.com/api/Token/WXVIPLogin'
        headers = {
            'buildingid': '01',
            'app_id': 'api.app.member',
            'Accept-Encoding': 'gzip,compress,br,deflate',
            'Content-Type': 'application/json',
            'User-Agent': r'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.31(0x18001f37) NetType/WIFI Language/zh_CN',
            'Referer': r'https://servicewechat.com/wx597e17303800393c/41/page-frame.html',
        }
        data1 = {
            "requestId": "v5.app.member.wechat",
            "openId": self.openid,
        }
        logger.info(f'--{data1} --->')
        res = requests.post(url_login, headers=headers, json=data1).json()
        # print('login --->', res)
        if 'data' not in res:
            return ''
        else:
            return res


    def checkin(self) -> dict:
        url_checkin = 'https://sjzhlh.com/api/Sign/SignIn'
        loginres = self.get_cookie()
        headers = {
            'Connection': 'keep-alive',
            'buildingid': '01',
            'Authorization': loginres['data']['tokentype']+' '+ loginres['data']['accesstoken'],
            'Accept-Encoding': 'gzip,compress,br,deflate',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.31(0x18001f37) NetType/WIFI Language/zh_CN',
            'Referer': 'https://servicewechat.com/wx597e17303800393c/40/page-frame.html'
        }
        res = requests.post(url_checkin, headers=headers, data='null').json()
        # print('checkin --->', res)
        logger.info(f'--{res} --->')
        if len(res['errorcode']) != 0 and res['errorcode'] != '37115':
            return res 
        msg_res = res["msg"] if res["msg"] else "签到成功"
        data = "获得"+str(res["data"]['integralamount'])+"积分" if res["data"] else "重复签到"
        msg = f"""欢乐汇签到：{msg_res}\n签到信息：{data}\n"""
        return msg
