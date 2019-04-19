# -*- coding:utf8 -*-

from django.conf.urls import url

from payment import views

urlpatterns = [
    # 添加视图url
    url(r'^api/pay/aliWapPay$', views.aliWapPay.as_view()),
    url(r'^api/pay/aliQrPay$', views.aliQrPay.as_view()),
    url(r'^api/pay/weixinQrPay$', views.weixinQrPay.as_view()),
    url(r'^api/pay/weixinJsApiPay$', views.weixinJsApiPay.as_view()),
    url(r'^api/pay/checkPayStatus', views.checkPayStatus.as_view()),
    url(r'^api/pay/skipThirdPay', views.skipThirdPay.as_view()),
]