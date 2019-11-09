#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
import json

BASE_URL = 'http://47.103.54.14:9069'

TOKEN_URL = '/api/auth/token'
CHECK_PICKING = '/api/sale_order/check_stock_picking'
DONE_PICKING = '/api/stock_picking/done_picking'
HEADERS = {
    'Content-Type': 'application/json',
    'charset': 'utf-8',
}

data = {
    'params': {
        'login': 'aop_interface_test_name',
        'password': 'aop_interface_test_password',
        'db': 'aop_interface_test_db'
    }
}

# 测试 获取 token
req = requests.post(url=BASE_URL + TOKEN_URL, data=json.dumps(data), headers=HEADERS)
content = json.loads(req.content.decode('utf-8'))
print(content)
# 返回值： {'jsonrpc': '2.0', 'result': '{"company_id": 1, "expires_in": "31536000", "uid": 27, "user_context": {"lang": "en_US", "uid": 27, "tz": "Asia/Shanghai"}, "access_token": "access_token_f772d5c69ca510ad54eb91c8d8072e9dd4a2538d"}', 'id': None}

result = json.loads(content.get('result'))
HEADERS.update({
    'access-token': result.get('access_token')
})
print('headers: ', HEADERS)
# 返回值： headers:  {'Content-Type': 'application/json', 'charset': 'utf-8', 'access-token': 'access_token_f772d5c69ca510ad54eb91c8d8072e9dd4a2538d'}

# 测试 I_WMS_AOP_001
data = {
    'params': {
        'partner_id': '长安民生',
        'vin': 'LVSFKAAU3KF775309',
        'product_id': '长安福特 (874MJ, 2)',
        'from_location_id': '重庆长安福特VDC库, CQ1VDC2',
        'to_location_id': '长安民生经销商, 红河万福汽车销售服务有限公司',
    }
}

res = requests.post(url=BASE_URL + CHECK_PICKING, data=json.dumps(data), headers=HEADERS)
content = json.loads(res.content.decode('utf-8'))
print(content)
# 返回值 {'jsonrpc': '2.0', 'result': '{"time": 1571821697.9281147, "method": "/api/sale_order/check_stock_picking", "code": 200}', 'id': None}

# 测试 I_WMS_AOP_002
data = {
    'params': {
        'partner_id': '长安民生',
        'vin': 'LVSFKAAU3KF775309',
        'product_id': '长安福特 (874MJ, 2)',
        'from_location_id': 'VDC/重庆长安福特VDC库',
        'to_location_id': 'TJCXB/团结村线边库',
        'picking_type_id': '短驳接车',
        'quantity_done': 1
    }
}

res = requests.post(url=BASE_URL + DONE_PICKING, data=json.dumps(data), headers=HEADERS)
content = json.loads(res.content.decode('utf-8'))
print(content)
# 返回值： {'jsonrpc': '2.0', 'result': '{"time": 1571821697.9542348, "method": "/api/stock_picking/done_picking", "code": 200}', 'id': None}


# 测试WMS
# 使用 zeep 发送数据
from requests import Session
from zeep.transports import Transport
from zeep import Client

session = Session()
session.verify = False
transport = Transport(session=session)

# 客户供应商
zeep_supplier_client = Client('https://222.66.94.66:9081/zjwms/ws/supplierInfo?wsdl', transport=transport)

data = [
    {
        'name': '陕西福腾汽车贸易有限公司',
        'code': 'A02121',
        'country_name': 'China',
        'state_name': '陕西省 (CN)',
        'city_name': '西安市',
        'street_name': '陕西省西安市未央区三桥西部车城陕西福腾汽车贸易有限公司'
    },
    {
        'name': '西昌市成品装卸搬运服务有限公司',
        'code': 'XC0533'
    },
    {
        'name': '重庆市禾宏物流有限公司',
        'code': 'A02323'
    }]
res = zeep_supplier_client.service.supplier(str(data))
print(res)


# 任务
data = [{
    'task_id': 589,
    'partner_name': '长安民生',
    'product_id': '福睿斯',
    'from_location_id': '福特二厂VDC库1',
    'to_location_id': '团结村线边库',
    'picking_type_name': '接车',
    'quantity_done': 1
}]
zeep_task_client = Client('https://222.66.94.66:9081/zjwms/ws/generationTask?wsdl', transport=transport)

res = zeep_supplier_client.service.sendToTask(str(data))
print(res)
