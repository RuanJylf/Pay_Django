from django.db import models

# Create your models here.
from pay_django.utils.models import BaseModel


class Orders(BaseModel):
    """
    订单信息
    """

    pay_status = (
        (1, "未支付"),
        (2, "已支付"),

    )

    # 定义订单表各字段约束
    orders_id = models.CharField(max_length=64, primary_key=True, verbose_name="订单序号")
    order_no = models.CharField(max_length=64, verbose_name="订单编号")
    pay_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="支付金额")
    pay_status = models.SmallIntegerField(default=1, verbose_name="订单状态", choices = pay_status)

    class Meta:
        db_table = "md_orders"
        verbose_name = '订单信息'
        verbose_name_plural = verbose_name


class Payment(BaseModel):
    """
    支付信息
    """
    # 定义支付表各字段约束
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, verbose_name='订单')
    trade_id = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="支付编号")

    class Meta:
        db_table = 'md_payment'
        verbose_name = '支付信息'
        verbose_name_plural = verbose_name
