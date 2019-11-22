#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
import json

BASE_URL = 'http://47.103.54.14:8069'
# BASE_URL = 'http://127.0.0.1:8069'

TOKEN_URL = '/api/auth/token'
DONE_PICKING = '/api/stock_picking/done_picking'
HEADERS = {
    'Content-Type': 'application/json',
    'charset': 'utf-8',
}

data = {
    'params': {
        'login': 'aop_interface_test_name',
        'password': 'aop_interface_test_password',
        'db': 'daodu_demo'
    }
}

# data = {
#     'params': {
#         'login': 'odoo',
#         'password': 'odoo',
#         'db': 'aopdata'
#     }
# }
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

# 接车数据
data = {
    'params': {
        'data': [{'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
                  'vin': 'LSY12345670000100', 'warehouse_code': 'WTJCXBK', 'warehouse_name': '团结村线边库'},
                 {'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
                  'vin': 'LSY12345670000101', 'warehouse_code': 'WTJCXBK', 'warehouse_name': '团结村线边库'},
                 {'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
                  'vin': 'LSY12345670000102', 'warehouse_code': 'WTJCXBK', 'warehouse_name': '团结村线边库'},
                 {'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
                  'vin': 'LSY12345670000103', 'warehouse_code': 'WTJCXBK', 'warehouse_name': '团结村线边库'}]
    }
}

# 完成任务
# 227, 236, 254, 245
# 测试 I_WMS_AOP_001
data = {
    'params': {
        'data': [
            # {
            #     'task_id': 227
            # },
            # {
            #     'task_id': 236,
            # },
            # {
            #     'task_id': 254
            # },
            {
                'task_id': 245
            }
        ]
    }
}

res = requests.post(url=BASE_URL + DONE_PICKING, data=json.dumps(data), headers=HEADERS)
content = json.loads(res.content.decode('utf-8'))
print(content)
# 返回值： {'jsonrpc': '2.0', 'result': '{"time": 1571821697.9542348, "method": "/api/stock_picking/done_picking", "code": 200}', 'id': None}


# # 测试WMS
# # 使用 zeep 发送数据
# from requests import Session
# from zeep.transports import Transport
# from zeep import Client
#
# session = Session()
# session.verify = False
# transport = Transport(session=session)
#
# # 客户供应商
# zeep_supplier_client = Client('https://222.66.94.66:9081/zjwms/ws/supplierInfo?wsdl', transport=transport)
#
#
# data = []
# for _ in range(1000):
#     tmp = {
#         'name': '陕西福腾汽车贸易有限公司',
#         'code': 'A02121',
#         'country_name': 'China',
#         'state_name': '陕西省 (CN)',
#         'city_name': '西安市',
#         'street_name': '陕西省西安市未央区三桥西部车城陕西福腾汽车贸易有限公司',
#         'time': time.time()
#     }
#
#     data.append(tmp)
# # data = [
# #     {
# #         'name': '陕西福腾汽车贸易有限公司',
# #         'code': 'A02121',
# #         'country_name': 'China',
# #         'state_name': '陕西省 (CN)',
# #         'city_name': '西安市',
# #         'street_name': '陕西省西安市未央区三桥西部车城陕西福腾汽车贸易有限公司'
# #     },
# #     {
# #         'name': '西昌市成品装卸搬运服务有限公司',
# #         'code': 'XC0533'
# #     },
# #     {
# #         'name': '重庆市禾宏物流有限公司',
# #         'code': 'A02323'
# #     }]
# res = zeep_supplier_client.service.supplier(str(data))
# print(res)
#
#
# # # 任务
# # data = [{
# #     'task_id': 589,
# #     'partner_name': '长安民生',
# #     'product_id': '福睿斯',
# #     'from_location_id': '福特二厂VDC库1',
# #     'to_location_id': '团结村线边库',
# #     'picking_type_name': '接车',
# #     'quantity_done': 1
# # }]
# # zeep_task_client = Client('https://222.66.94.66:9081/zjwms/ws/generationTask?wsdl', transport=transport)
#
# # res = zeep_task_client.service.sendToTask(str(data))
# # print(res)
