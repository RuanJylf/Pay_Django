# -*- coding:utf8 -*-


# ========== 微信支付相关配置信息 ===========

import fcntl
import hashlib
import os
import socket
import struct
import time
import qrcode
import requests

from collections import OrderedDict
from random import Random
from bs4 import BeautifulSoup


APP_ID = "wx6fc0848fc64f6ca9"  # 公众号的appid
APP_SECRECT = "f641a0e8fa69ff16b238915202c81172"  # 公众号秘钥

MCH_ID = "1343351101"  # 商户号
API_KEY = "d855daef2a0e596bdac8dc30f51ca7ff"  # 微信商户平台生成API秘钥

UFDODER_URL = "https://api.mch.weixin.qq.com/sandboxnew/pay/unifiedorder"  # 微信下单测试api, 模拟测试
NOTIFY_URL = "http://pgy.lingxiu.top/QDYM/orderList.html"  # 微信支付结果回调接口, 改为服务器上处理结果回调的方法路径, 模拟测试


def get_ip(ifname):
    """
    获取本机IP地址
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname[:15],'utf-8')))[20:24])

CREATE_IP = get_ip('ens33')  # 本机服务器的IP(Linux)


# ========== 微信扫码支付相关方法工具 ==========

def random_str(randomlength):
    """
    生成随机字符串, 有效字符 a-z A-Z 0-9
    :param randomlength: 字符串长度
    :return: 随机字符串
    """
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        str += chars[random.randint(0, length)]
    return str


def get_sign(data_dict, key):
    """
    签名生成函数，参数为签名的数据和密钥
    :param data_dict: 参数， dict对象
    :param key: API 密钥
    :return: sign string
    """
    params_list = sorted(data_dict.items(), key=lambda e: e[0], reverse=False)  # 参数字典倒排序为列表
    # 组织参数字符串并在末尾添加商户交易密钥
    params_str = "&".join(u"{}={}".format(k, v) for k, v in params_list) + '&key=' + key

    md5 = hashlib.md5()  # 使用MD5加密模式
    md5.update(params_str.encode('utf-8'))  # 将参数字符串传入
    sign = md5.hexdigest().upper()  # 完成加密并转为大写
    return sign


def trans_dict_to_xml(data_dict):
    """
    定义字典转XML的函数, 将 Dict 对象转换成微信支付交互所需的 XML 格式数据
    :param data_dict: Dict 对象
    :return: xml 格式数据
    """
    data_xml = []
    for k in sorted(data_dict.keys()):  # 遍历字典排序后的key
        v = data_dict.get(k)  # 取出字典中key对应的value
        if k == 'detail' and not v.startswith('<![CDATA['):  # 添加XML标记
            v = '<![CDATA[{}]]>'.format(v)
        data_xml.append('<{key}>{value}</{key}>'.format(key=k, value=v))
    return '<xml>{}</xml>'.format(''.join(data_xml)).encode('utf-8')  # 返回XML，并转成utf-8，解决中文的问题


def trans_xml_to_dict(data_xml):
    """
    定义XML转字典的函数, 将微信支付交互返回的 XML 格式数据转化为 Python Dict 对象
    :param xml: 原始 XML 格式数据
    :return: dict 对象
    """
    # 解析XML
    soup = BeautifulSoup(data_xml, features='xml')
    xml = soup.find('xml')
    if not xml:
        return {}
    data_dict = dict([(item.name, item.text) for item in xml.find_all()])
    print("微信验证: %s" % data_dict)
    return data_dict


def wx_pay_unifiedorde(detail):
    """
    访问微信支付统一下单接口
    :param detail: 订单详情
    :return: 下单信息
    """
    detail['sign'] = get_sign(detail, API_KEY)
    xml = trans_dict_to_xml(detail)  # 转换字典为XML
    response = requests.request('post', UFDODER_URL, data=xml)  # 以POST方式向微信公众平台服务器发起请求
    # data_dict = trans_xml_to_dict(response.content)  # 将请求返回的数据转为字典
    # print("content: %s" % response.content)  # 模拟测试
    return response.content


def pay_fail(err_msg):
    """
    微信支付失败
    :param err_msg: 失败原因
    """
    data_dict = {'return_msg': err_msg, 'return_code': 'FAIL'}
    return trans_dict_to_xml(data_dict)


def create_qrcode(order_no, url):
    """
    生成扫码支付二维码
    :param order_no: 订单编号
    :param url: 支付路由
    """
    qrcode_name = "weixin_" + order_no + ".png"  # 二维码图片名称
    img = qrcode.make(url)  # 生成二维码图片
    img_url = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) +'/apps/payment/images/' + qrcode_name
    img.save(img_url)  # 保存图片
    return img_url


def get_redirect_url():
    """
    获取微信返回的重定向的url
    :return: url,其中携带code
    """
    # 微信授权url, 获取code, state
    WeChatcode = 'https://open.weixin.qq.com/connect/oauth2/authorize'
    urlinfo = OrderedDict()
    urlinfo['appid'] = APP_ID
    urlinfo['redirect_uri'] = 'http://pgy.lingxiu.top/QDYM/orderList.html'  # 设置重定向路由
    urlinfo['response_type'] = 'code'
    urlinfo['scope'] = 'snsapi_base'  # 只获取基本信息
    urlinfo['state'] = 'mywxpay'  # 自定义的状态码

    info = requests.get(url=WeChatcode, params=urlinfo)
    print("微信授权链接: %s" % info.url)  # 测试输出
    return info.url, urlinfo


def get_openid(code, state):
    """
    获取微信的openid
    """
    if code and state == 'mywxpay':
        # 授权回调, 利用code, state获取access_token, 在获取openid
        WeChatcode = 'https://api.weixin.qq.com/sns/oauth2/access_token'
        urlinfo = OrderedDict()
        urlinfo['appid'] = APP_ID
        urlinfo['secret'] = APP_SECRECT
        urlinfo['code'] = code
        urlinfo['grant_type'] = 'authorization_code'
        info = requests.get(url=WeChatcode, params=urlinfo)
        info_dict = eval(info.content.decode('utf-8'))
        print("获取openid链接: %s" % info.url)  # 测试输出

        try:
            openid = info_dict['openid']
            return openid
        except Exception as e:
            return None


def get_native_params(order):
    """
     获取微信的二维码支付需要的参数
     :param order: 订单信息
     """
    order_no = order.order_no
    pay_amount = order.pay_amount

    # 微信扫码支付参数字典
    params = {
        'appid': APP_ID,  # 公众账号ID
        'mch_id': MCH_ID,  # 商户号
        'nonce_str': random_str(16),  # 随机字符串
        'body': '蒲公英-商城购物',  # 商品描述信息
        'out_trade_no': order_no,  # 商户订单号
        'total_fee': int(pay_amount * 100),  # 订单总金额, 付款金额，单位是分，必须是整数
        'spbill_create_ip': CREATE_IP,  # 发送请求服务器的IP地址
        'notify_url': NOTIFY_URL,  # 支付成功后微信回调路由, 告知商户支付结果
        'trade_type': 'NATIVE',
    }
    params['sign'] = get_sign(params, API_KEY)  # 添加签名到参数字典

    return params


def get_jsapi_params(order, openid):
    """
    获取微信的JsApi支付需要的参数
    :param order: 订单信息
    :param openid: 用户的openid
    """
    order_no = order.order_no
    pay_amount = order.pay_amount

    # 微信扫码支付和公众号支付共同参数字典
    params = {
        'appid': APP_ID,  # 公众账号ID
        'mch_id': MCH_ID,  # 商户号
        'nonce_str': random_str(16),  # 随机字符串
        'body': '蒲公英-商城购物',  # 商品描述
        'out_trade_no': order_no,  # 商户订单号
        'total_fee': int(pay_amount * 100),  # 订单总金额, 付款金额，单位是分，必须是整数
        'spbill_create_ip': CREATE_IP,  # 发送请求服务器的IP地址
        'notify_url': NOTIFY_URL,  # 支付成功后微信回调路由, 通知地址
        'openid': openid,  # 公众号获取的openid
        'trade_type': 'JSAPI',  # 公众号支付类型
        'time_stamp': int(time.time()),  # 时间戳
        'sign_type': 'MD5',  # 签名方式
    }

    # 调用微信统一下单支付接口url
    notify_result = wx_pay_unifiedorde(params)
    # params['prepay_id'] = trans_xml_to_dict(notify_result)['prepay_id']

    params['prepay_id'] = order_no  # 预支付交易会话标识
    params['package'] = 'prepay_id=' + params['prepay_id']
    params['sign'] = get_sign({'appid': APP_ID,
                               "time_stamp": params['time_stamp'],
                               'nonce_str': params['nonce_str'],
                               'package': params['package'],
                               'sign_type': params['sign_type'],
                               },
                              API_KEY)
    return params
