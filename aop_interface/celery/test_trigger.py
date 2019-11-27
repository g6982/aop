# /usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from aop_receive_from_wms import send_to_localhost_data

data = {'picking_ids': [
    {'task_id': 11128, 'product_name': '福睿斯', 'product_color': '1', 'product_model': '874', 'product_config': 'MK',
     'supplier_name': '重庆上源货运代理有限公司', 'warehouse_code': 'STJCZ', 'quantity_done': 1, 'brand_model_name': '长安福特',
     'from_location_id': '团结村站', 'to_location_id': '团结村站', 'to_location_type': 'internal', 'partner_name': '长安民生',
     'vin': 'WW000000000000113', 'picking_type_name': '加固', 'batch_id': 600, 'scheduled_date': '2019-11-26 06:52:48'},
    {'task_id': 11137, 'product_name': '福睿斯', 'product_color': '1', 'product_model': '874', 'product_config': 'MK',
     'supplier_name': '重庆上源货运代理有限公司', 'warehouse_code': 'STJCZ', 'quantity_done': 1, 'brand_model_name': '长安福特',
     'from_location_id': '团结村站', 'to_location_id': '团结村站', 'to_location_type': 'internal', 'partner_name': '长安民生',
     'vin': 'WW000000000000114', 'picking_type_name': '加固', 'batch_id': 600, 'scheduled_date': '2019-11-26 06:52:48'}]}

for _ in range(10):
    send_to_localhost_data.delay(30)
print('done')


