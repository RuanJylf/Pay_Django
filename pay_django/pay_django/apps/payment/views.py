# -*- coding:utf8 -*-

import json

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from payment import alipay
from payment.models import Orders
from pay_django.utils.weixin import *


class aliWapPay(APIView):
    """
    支付宝手机网页支付基本逻辑
    1.获取参数
    2.校验参数
    3.查询订单支付信息
    4.支付宝手机网页支付
    5.支付结果通知回调
    6.更新订单支付状态
    """

    # POST  /api/pay/aliWapPay
    def post(self, request):
        """支付宝手机网页支付"""

        # 1.获取参数
        # post请求数据参数 bytes -> str -> dict
        data_str = request.body.decode("utf-8")
        data_dict = json.loads(data_str)
        print("参数字典: %s" % data_dict)  # 测试输出

        token = data_dict['token']
        orders_id = data_dict['orders_id']

        # 2.校验参数
        # 判断用户是否登陆
        if not token:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '用户未登录'})

        # 判断订单序号是否存在
        if not orders_id:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '缺少参数'})

        # 3.查询订单支付信息: 订单编号, 支付金额
        try:
            order = Orders.objects.get(orders_id=orders_id)
            order_no = order.order_no
            pay_amount = order.pay_amount
        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '数据库查询错误'})

        # 4.支付宝手机网页支付
        # 构造订单支付参数字符串
        order_string = alipay.api_alipay_trade_wap_pay(
            out_trade_no=order_no,  # 订单编号
            total_amount=str(pay_amount),  # 支付金额
            subject='蒲公英-商城购物',  # 订单主题
            return_url="http://pgy.lingxiu.top/QDYM/orderList.html",  # 支付成功回调地址
            notify_url=None  # 支付结果通知地址
        )

        # 利用订单支付参数字符串拼接网页支付链接网址
        pay_url = settings.ALIPAY_URL + '?' + order_string
        print("支付链接: %s" % pay_url)  # 测试输出

        # 重定向到支付网页地址
        # return HttpResponseRedirect(pay_url)

        data = {
            "pay_url": pay_url
        }
        return Response({'code': status.HTTP_200_OK, 'message': '操作成功', 'data': data})

    # 支付结果通知回调 notify
    def aliNotify(self, request):
        """支付宝支付结果通知回调"""

        data = request.form.to_dict()

        # sign 不能参与签名验证
        signature = data.pop("sign")
        print(signature)

        # 3.查询订单支付信息: 订单编号, 支付金额
        try:
            order = Orders.query.filter(Orders.order_no == data.get("out_trade_no")).first()
        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '数据库查询错误'})

        # 支付状态验证
        success = alipay.verify(data, signature)
        if success and data["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            # 更新订单支付状态
            order.pay_status = 1
            print("支付成功！")
        else:
            print("尚未支付！")


class aliQrPay(APIView):
    """
    支付宝扫码支付基本逻辑
    1.获取参数
    2.校验参数
    3.查询订单支付信息
    4.支付宝扫码支付
    5.支付结果通知回调
    6.更新订单支付状态
    """

    # POST  /api/pay/aliQrPay
    def post(self, request):
        """支付宝扫码支付"""

        # 1.获取参数
        # post请求数据参数 bytes -> str -> dict
        data_str = request.body.decode("utf-8")
        data_dict = json.loads(data_str)
        print("参数字典: %s" % data_dict)  # 测试输出

        token = data_dict['token']
        orders_id = data_dict['orders_id']

        # 2.校验参数
        # 判断用户是否登陆
        if not token:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '用户未登录'})

        # 判断订单序号是否存在
        if not orders_id:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '缺少参数'})

        # 3.查询订单信息: 订单编号, 支付金额
        try:
            order = Orders.objects.get(orders_id=orders_id)
            order_no = order.order_no
            pay_amount = order.pay_amount
        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '数据库查询错误'})

        # 4.支付宝扫码支付, 返回支付二维码图片地址
        # 生成预付订单信息
        result = alipay.api_alipay_trade_precreate(
            subject="蒲公英-商城购物",
            out_trade_no=order_no,
            total_amount=str(pay_amount),
        )
        # 获取预付订单支付url
        code_url = result.get('qr_code')
        print(code_url)

        # 利用支付链接生成支付二维码
        qrcode_name = "alipay_" + order_no + ".png"  # 二维码图片名称
        img = qrcode.make(code_url)  # 生成二维码图片
        img_url = os.path.dirname(os.path.abspath(__file__)) +'/images/' + qrcode_name
        img.save(img_url)  # 保存图片
        print("图片地址: %s" % img_url)  # 测试输出

        # 支付宝扫码支付结果通知回调
        # 检查订单状态
        paid = False
        for i in range(10):
            # 每3s检查一次， 共检查10次
            print("等待 3s")
            time.sleep(3)
            result = alipay.api_alipay_trade_query(out_trade_no=order_no)
            if result.get("trade_status", "") == "TRADE_SUCCESS":
                paid = True
                # 更新订单支付信息
                order.pay_status = 1
                print("支付成功！")
                break
            print("尚未支付！")

        # 30s内未支付, 取消订单
        if paid is False:
            alipay.api_alipay_trade_cancel(out_trade_no=order_no)

        data = {
            "qrcode": img_url
        }
        return Response({'code': status.HTTP_200_OK, 'message': '操作成功', 'data': data})


class weixinJsApiPay(APIView):
    """
    微信公众号支付基本逻辑
    1.获取参数
    2.校验参数
    3.查询订单支付信息
    4.微信公众号支付
    5.支付结果通知回调
    6.更新订单支付状态
    """

    # POST  /api/pay/weixinJsApiPay
    def post(self, request):

        # 1.获取参数
        # post请求数据参数 bytes -> str -> dict
        data_str = request.body.decode("utf-8")
        data_dict = json.loads(data_str)
        print("参数字典: %s" % data_dict)  # 测试输出

        orders_id = data_dict['orders_id']
        get_info = data_dict['get_info']
        openid = request.COOKIES.get('openid', '')
        # openid = data_dict['openid']

        # 2.校验参数
        # 判断订单序号是否存在
        if not orders_id:
            data = {
            }
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '缺少参数'})

        if not openid:
            # 未获取到openid
            if get_info == '0':
                # 构造一个url，携带一个重定向的路由参数，
                # 然后访问微信的一个url,微信会回调你设置的重定向路由，并携带code参数
                url = get_redirect_url()[0]
                return HttpResponseRedirect(url)
            else:
                # 获取用户的openid
                urlinfo = get_redirect_url()[1]
                print("用户信息: %s" % urlinfo)
                code = urlinfo["response_type"]
                state = urlinfo["state"]
                openid = get_openid(code, state)

        # 3.查询订单信息
        try:
            order = Orders.objects.get(orders_id=orders_id)
        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '数据库查询错误'})

        # 4.微信公众号支付
        # 获取支付订单参数
        params = get_jsapi_params(order, openid)
        print("参数字典: %s" % params)

        # 构造支付参数
        pay_param = {
            'appId': params['appid'],
            'timeStamp': params['time_stamp'],
            'nonceStr': params['nonce_str'],
            'package': params['package'],
            'signType': "MD5",
            'paySign': params['sign'],
        }
        print("支付参数: %s" % pay_param)

        # 利用支付参数拼接支付链接
        pay_url = "weixin://wxpay/bizpayurl?appid=%s&time_stamp=%s&nonce_str=%s&package=%s&sign_type=%s&pay_sign=%s" \
                  % (pay_param['appId'], pay_param['timeStamp'], pay_param['nonceStr'],
                     pay_param['package'], pay_param['signType'], pay_param['paySign'])
        print("支付链接: %s" % pay_url)  # 测试输出
        # return HttpResponseRedirect(pay_url)

        data = {
            "pay_param": pay_param
        }
        return Response({'code': status.HTTP_200_OK, 'message': '操作成功', 'data': data})

    # TODO 微信支付结果通知回调 notify

    # TODO 更新订单支付状态 update_status


class weixinQrPay(APIView):
    """
    微信扫码支付基本逻辑
    1.获取参数
    2.校验参数
    3.查询订单信息
    4.微信扫码支付
    5.支付结果通知回调
    6.更新订单支付状态
    """

    # POST  /api/pay/weixinQrPay
    def post(self, request):

        # 1.获取参数
        # post请求数据参数 bytes -> str -> dict
        data_str = request.body.decode("utf-8")
        data_dict = json.loads(data_str)
        print("参数字典: %s" % data_dict)  # 测试输出

        token = data_dict['token']
        orders_id = data_dict['orders_id']

        # 2.校验参数
        # 判断用户是否登陆
        if not token:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '用户未登录'})

        # 判断订单序号是否存在
        if not orders_id:
            data = {

            }
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '缺少参数'})

        # 3.查询订单信息: 订单编号
        try:
            order = Orders.objects.get(orders_id=orders_id)
            order_no = order.order_no
        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '数据库查询错误'})

        # 4.微信扫码支付
        # 获取支付订单参数
        params = get_native_params(order)
        print("参数字典: %s" % params)

        # 模拟测试
        pay_dict = {
            'appid': APP_ID,  # 公众账号ID
            'mch_id': MCH_ID,  # 商户号
            'nonce_str': random_str(16),  # 随机字符串
            'time_stamp': int(time.time()),  # 时间戳
            'product_id': order_no,  # 商品信息或订单编号
            'sign': params['sign'],
        }

        # 构造支付链接
        pay_dict[
            'code_url'] = "weixin://wxpay/bizpayurl?appid=%s&mch_id=%s&nonce_str=%s&product_id=%s&time_stamp=%s&sign=%s" \
                          % (pay_dict['appid'], pay_dict['mch_id'], pay_dict['nonce_str'], pay_dict['product_id'],
                             pay_dict['time_stamp'],
                             pay_dict['sign'])
        pay_dict['return_code'] = "SUCCESS" if pay_dict['code_url'] else "Fail"

        # xml = trans_dict_to_xml(params)  # 转换字典为XML
        # response = requests.request('post',UFDODER_URL, data=xml)  # 以POST方式向微信公众平台服务器发起请求
        # pay_dict = trans_xml_to_dict(response.content)  # 将请求返回的数据转换为字典
        print("回调字典: %s" % pay_dict)

        # 生成微信扫码支付链接， 必须在微信客户端打开
        code_url = pay_dict.get('code_url')
        print("支付链接: %s" % code_url)

        if pay_dict.get('return_code') == 'SUCCESS':  # 如果请求成功
            # 利用支付链接生成二维码
            img_url = create_qrcode(order_no, code_url)
            print("二维码地址: %s" % img_url)  # 测试输出

            data = {
                "qrcode": img_url
            }
            return Response({'code': status.HTTP_200_OK, 'message': '操作成功', 'data': data})
        else:
            # return_code = Fail, 获取code_url失败
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '获取url失败'})

    # TODO 支付结果通知回调 notify

    # TODO 更改订单支付状态 update_status


class checkPayStatus(APIView):
    """
    支付检测基本逻辑
    1.获取参数
    2.校验参数
    3.查询订单信息
    4.判断订单支付状态
    5.返回订单支付状态
    """

    # POST  /api/pay/checkPayStatus
    def post(self, request):

        # 1.获取参数
        # post请求数据参数 bytes -> str -> dict
        data_str = request.body.decode("utf-8")
        data_dict = json.loads(data_str)
        print("参数字典: %s" % data_dict)  # 测试输出

        token = data_dict['token']
        orders_id = data_dict['orders_id']

        # 2.校验参数
        # 判断用户是否登陆
        if not token:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '用户未登录'})

        # 判断订单序号是否存在
        if not orders_id:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '缺少参数'})

        # 3.查询订单支付信息: 支付状态
        try:
            order = Orders.objects.get(orders_id=orders_id)
            pay_status = order.pay_status
        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '数据库查询错误'})

        # 4.判断支付状态
        if pay_status in [0, 1]:
            data = {
                "pay_status": pay_status
            }
            # 返回支付状态
            print("支付状态 %s" % pay_status)  # 测试输出

            # 模拟测试
            if pay_status:
                # 支付状态为1, 已支付
                print("订单已支付！")
            else:
                # 支付状态为0, 未支付
                print("订单未支付！")
            return Response({'code': status.HTTP_200_OK, 'message': '操作成功', 'data': data})
        else:
            # 支付状态参数错误
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '参数错误'})


class skipThirdPay(APIView):
    """
    无需支付基本逻辑
    1.获取参数
    2.校验参数
    3.查询订单信息
    4.判断支付金额和支付状态
    5.返回响应
    """

    # POST  /api/pay/skipThirdPay
    def post(self, request):

        # 1.获取参数
        # post请求数据参数 bytes -> str -> dict
        data_str = request.body.decode("utf-8")
        data_dict = json.loads(data_str)
        print("参数字典: %s" % data_dict)  # 测试输出

        token = data_dict['token']
        orders_id = data_dict['orders_id']

        # 2.校验参数
        # 判断用户是否登陆
        if not token:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '用户未登录'})

        # 判断订单序号是否存在
        if not orders_id:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '缺少参数'})

        # 3.查询订单信息: 支付金额, 支付状态
        try:
            order = Orders.objects.get(orders_id=orders_id)
            pay_amount = order.pay_amount
            pay_status = order.pay_status

        except Orders.DoesNotExist:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '订单查询错误'})

        # 4.判断支付金额是否为0.00
        if pay_amount == "0.00" or pay_status == 1:
            # 如果支付金额为0.00 或者订单支付状态为1已支付, 无需支付
            data = {
            }
            print("无需支付, 请前往商城选购商品！")
            return Response({'code': status.HTTP_200_OK, 'message': '操作成功', 'data': data})
        elif pay_amount != "0.00" and pay_status == 0:
            # 支付金额不为0.00, 支付状态为0未支付, 前往支付
            print("订单尚未支付, 请前往支付！")
            return Response({'code': status.HTTP_200_OK, 'message': '操作成功'})
        else:
            return Response({'code': status.HTTP_400_BAD_REQUEST, 'message': '参数错误'})
