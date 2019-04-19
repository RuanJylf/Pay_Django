# -*- coding:utf8 -*-

# 构造支付宝支付工具
import os

from alipay import AliPay

# 构造支付宝支付工具
alipay = AliPay(
    appid="2016092700611737",  # 支付宝appid
    app_notify_url=None,  # 默认回调url
    app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
    alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/alipay_public_key.pem"),
    sign_type="RSA2",  # RSA 或者 RSA2
    debug=True  # 默认False
)
