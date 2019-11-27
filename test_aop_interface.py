#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
import string
import requests
import json
import pprint

# BASE_URL = 'http://47.103.54.14:8069'
BASE_URL = 'http://127.0.0.1:8069'
# BASE_URL = 'http://192.168.13.177:8069'

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

data = {
    'params': {
        'login': 'odoo',
        'password': 'odoo',
        'db': 'aop27'
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

# salt = ''.join(random.sample(string.ascii_letters + string.digits, 8))


# def get_17_vin():
#     return ''.join(random.sample(string.ascii_letters + string.digits, 17))
#
#
# def send_data_test(loop_time):
#     warehouse_code = 'WTJCXBK'
#     warehouse_name = '团结村线边库'
#     for _ in range(loop_time):
#         data = {
#             'params': {
#                 'data': [{'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
#                           'vin': get_17_vin(), 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name},
#                          ]
#             }
#         }
#         res = requests.post(url=BASE_URL + DONE_PICKING, data=json.dumps(data), headers=HEADERS)
#         content = json.loads(res.content.decode('utf-8'))
#     print(content)
#
#
# if __name__ == '__main__':
#     send_data_test(300)


# # SLRZ/雒容站
# # WTJZXBK/唐家沱线边库
# # WTJCXBK/团结村线边库
# # WXZTLK/新筑铁路库
# warehouse_code = 'WTJCXBK'
# warehouse_name = '团结村线边库'
# # 接车数据
# data = {
#     'params': {
#         'data': [{'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
#                   'vin': 'WW000000000000113', 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name},
#                  {'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
#                   'vin': 'WW000000000000115', 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name}
#                  ]
#     }
# }
#
# # 完成任务
# # 227, 236, 254, 245
# # 测试 I_WMS_AOP_001
data = {
    'params': {
        'data': [
            {
                'task_id': 43,
                'sequence_id': 3
            },

        ]
    }
}
# SLRZ/雒容站
# WTJZXBK/唐家沱线边库
# WTJCXBK/团结村线边库
# WXZTLK/新筑铁路库
warehouse_code = 'WTJCXBK'
warehouse_name = '团结村线边库'
# 接车数据
# data = {
#     'params': {
#         'data': [{'brand_model_name': 'CQ2VDC1', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
#                   'vin': 'XX0001', 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name},
#                  # {'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
#                  #  'vin': 'WW000000000000004', 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name},
#                  # {'brand_model_name': 'CQ1VDC2', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
#                  #  'vin': 'WW000000000000005', 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name}
#                  ]
#     }
# }

data = {
    'params': {
        'data': []
    }
}

data_lst = data['params']['data']

source_date = [('LVSHJCAL5KE911041', '87K'),('LVSHFFAU2KS911432', '874'),('LVSHFFAU2KS911477', '874'),('LVSHFFAU3KS911438', '874'),
                   ('LVSHFFAU5KS911702', '874'),('LVSHFFAU3KS911441', '874'),('LVSHFFAU7KS910681', '874'),('LVSHFFAU0KS910893', '874'),
                   ('LVSHJCAL6KE908925', '87K'),('LVSHFFAUXKS911744', '874'),('LVSHFFAU8KS911435', '874'),('LVSHFFAU9KS911752', '874'),
                   ('LVSHFFAUXKS911436', '874'),('LVSHFFAU5KS911750', '874'),('LVSHJCAL0KE910136', '87K'),('LVSHJCAL5KE910083', '87K'),
                   ('LVSHFFAU1KS911745', '874'),('LVSHFFAUXKS910786', '874'),('LVSHJCAL8KE908926', '87K'),('LVSHFFAU7KS911457', '874'),
                   ('LVSHFFAU3KS911455', '874'),('LVSHFFAU1KS910949', '874'),('LVSHFFAU0KS911445', '874'),('LVSHFFAU4KS911450', '874'),
                   ('LVSHJCAL5KE910102', '87K'),('LVSHFFAU0KS910960', '874'),('LVSHFFAU2KS911429', '874'),('LVSHFFAU8KS911421', '874'),
                   ('LVSHFFAUXKS911453', '874'),('LVSHFFAU6KS910848', '874'),('LVSHJCAL3KE908879', '87K'),('LVSHFFAU6KS911451', '874'),
                   ('LVSHFFAU5KS908220', '874'),('LVSHFFAU4KS911741', '874'),('LVSHFFAU5KS911439', '874'),('LVSHFFAU4KS911447', '874'),
                   ('LVSHFFAU8KS911449', '874'),('LVSHFFAUXKS911758', '874'),('LVSHFFAU8KS911452', '874'),('LVSHFFAU0KS911414', '874'),
                   ('LVSHJCAL2KE909988', '87K'),('LVSHJCAL3KE910048', '87K'),('LVSHJCAL1KE910047', '87K')]
tml = {'brand_model_name': 'CQ2VDC1', 'product_color': 'YG4F', 'product_model': '874', 'state_flag': 'T',
                 'vin': 'XX0001', 'warehouse_code': warehouse_code, 'warehouse_name': warehouse_name}

for item in source_date:
    tml['vin'] = item[0]
    tml['product_model'] = item[1]
    data_lst.append(tml)
pprint.pprint(data_lst)
# # 完成任务
# # 227, 236, 254, 245
# # 测试 I_WMS_AOP_001
# data = {
#     'params': {
#         'data': [
#             # {
#             #     'task_id': 11,
#             # },
#             # {
#             #     'task_id': 20,
#             # },
#             # {
#             #     'task_id': 29,
#             # },
#             {
#                 'task_id': 30,
#                 # 'batch_id': 2
#             }
#         ]
#     }
# }

res = requests.post(url=BASE_URL + DONE_PICKING, data=json.dumps(data), headers=HEADERS)
content = json.loads(res.content.decode('utf-8'))
print(content)
# # 返回值： {'jsonrpc': '2.0', 'result': '{"time": 1571821697.9542348, "method": "/api/stock_picking/done_picking", "code": 200}', 'id': None}


# 测试WMS
# 使用 zeep 发送数据
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
# zeep_picking_client = Client('https://222.66.94.66:9081/zjwms/ws/generationTask?wsdl', transport=transport)
#
# # data = []
# # for _ in range(1000):
# #     tmp = {
# #         'name': '陕西福腾汽车贸易有限公司',
# #         'code': 'A02121',
# #         'country_name': 'China',
# #         'state_name': '陕西省 (CN)',
# #         'city_name': '西安市',
# #         'street_name': '陕西省西安市未央区三桥西部车城陕西福腾汽车贸易有限公司',
# #         'time': time.time()
# #     }
# #
# #     data.append(tmp)
# # # data = [
# # #     {
# # #         'name': '陕西福腾汽车贸易有限公司',
# # #         'code': 'A02121',
# # #         'country_name': 'China',
# # #         'state_name': '陕西省 (CN)',
# # #         'city_name': '西安市',
# # #         'street_name': '陕西省西安市未央区三桥西部车城陕西福腾汽车贸易有限公司'
# # #     },
# # #     {
# # #         'name': '西昌市成品装卸搬运服务有限公司',
# # #         'code': 'XC0533'
# # #     },
# # #     {
# # #         'name': '重庆市禾宏物流有限公司',
# # #         'code': 'A02323'
# # #     }]
# # res = zeep_supplier_client.service.supplier(str(data))
# # print(res)
#
#
# # 任务
# data = [{'task_id': 71, 'product_name': '福睿斯', 'product_color': '1', 'product_model': '874', 'product_config': 'EM',
#          'supplier_name': '重庆上源货运代理有限公司', 'warehouse_code': 'WTJCXBK', 'quantity_done': 1, 'brand_model_name': '长安福特',
#          'from_location_id': '团结村线边库', 'to_location_id': '团结村站', 'to_location_type': 'internal', 'partner_name': '长安民生',
#          'vin': 'LVSHFFAU3KS911441', 'picking_type_name': '装车', 'batch_id': 1,
#          'scheduled_date': '2019-11-27 07:15:42'},
#         {'task_id': 80, 'product_name': '福睿斯', 'product_color': '1', 'product_model': '874', 'product_config': 'EM',
#          'supplier_name': '重庆上源货运代理有限公司', 'warehouse_code': 'WTJCXBK', 'quantity_done': 1, 'brand_model_name': '长安福特',
#          'from_location_id': '团结村线边库', 'to_location_id': '团结村站', 'to_location_type': 'internal', 'partner_name': '长安民生',
#          'vin': 'LVSHFFAU7KS910681', 'picking_type_name': '装车', 'batch_id': 1,
#          'scheduled_date': '2019-11-27 07:15:42'},
#         {'task_id': 89, 'product_name': '福睿斯', 'product_color': '1', 'product_model': '874', 'product_config': 'EM',
#          'supplier_name': '重庆上源货运代理有限公司', 'warehouse_code': 'WTJCXBK', 'quantity_done': 1, 'brand_model_name': '长安福特',
#          'from_location_id': '团结村线边库', 'to_location_id': '团结村站', 'to_location_type': 'internal', 'partner_name': '长安民生',
#          'vin': 'LVSHFFAU0KS910893', 'picking_type_name': '装车', 'batch_id': 1,
#          'scheduled_date': '2019-11-27 07:15:42'}]
#
# res = zeep_picking_client.service.sendToTask(str(data))
# print(res)

# [{
#     'vin': 'LVSHFFAU6KS848090',
#     'task_id': 2,
#     'picking_type_name': '装车'
# },{
#     'vin': 'LVSHFFAU6KS848089',
#     'task_id': 1,
#     'picking_type_name': '铁路装车'
# },{
#     'vin': 'LVSHFFAU6KS848091',
#     'task_id': 3,
#     'picking_type_name': '短驳接车'
# }...]
