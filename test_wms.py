#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from requests import Session
from zeep.transports import Transport
from zeep import Client
import random

session = Session()
session.verify = False
transport = Transport(session=session)

VIN_TEST = [
    'LSGNB83L5KA712387',
    'LSGNB83L5KA712388',
    'LSGNB83L5KA712383',
    'LSGNB83L5KA712382',
    'LSGNB83L5KA712389',
    'LSGNC83L5KA001126',
    'LSGNC83L5KA001125',
    'LSGNC83L5KA001124',
    'LSGNC83L5KA001123'
]

VIN_TEST = [
    'LSGNB83L5KA712387',
    'LSGNB83L5KA712388',
    'LSGNB83L5KA712383'
]

VIN_TEST = [
    'LSGNB83L5KA001121',
    'LSGNB83L5KA111128',
    'LSGNB23L5KA711112'
]

SUPPLIER_FIELD_DICT = {
    'name': 'name',
    'ref': 'code',
    'country_id': 'country_name',
    'state_id': 'state_name',
    'city_id': 'city_name',
    'district_id': 'district_name',
    'street': 'street_name'
}
supplier_url = 'https://222.66.94.66:9081/zjwms/ws/supplierInfo?wsdl'
task_url = 'https://222.66.94.66:9081/zjwms/ws/generationTask?wsdl'
stock_url = 'https://222.66.94.66:9081/zjwms/ws/searchInventory?wsdl'

# 客户供应商
zeep_supplier_client = Client('https://222.66.94.66:9081/zjwms/ws/supplierInfo?wsdl', transport=transport)

# 任务
zeep_task_client = Client('https://222.66.94.66:9081/zjwms/ws/generationTask?wsdl', transport=transport)

# 库存检查
zeep_check_stock_client = Client('https://222.66.94.66:9081/zjwms/ws/searchInventory?wsdl', transport=transport)

picking_batch_id = self.env['stock.picking.batch']


def get_all_format_picking_data(picking_ids):
    data = []
    for picking_id in picking_ids:
        tmp = picking_batch_id._format_picking_data(picking_id)
        tmp.update({
            'vin': random.choice(VIN_TEST)
        })
        data.append(tmp)
    return data


def send_normal_picking_data(loop_time):
    picking_ids = self.env['stock.picking'].search([
        ('picking_type_id.name', 'like', '装车')
    ])
    loading_plan = self.env['stock.picking.batch'].browse(78).send_vehicle_loading_plan_to_wms()
    for _ in range(loop_time):
        picking_ids = [random.choice(picking_ids) for _ in range(random.randint(10, 20))]

        # 发送带有装车计划的数据
        data = get_all_format_picking_data(picking_ids)
        post_data = {
            'picking_ids': data,
            'loading_plan': loading_plan
        }
        print('post_data: ', post_data)
        result = zeep_task_client.service.sendToTask(json.dumps(post_data, ensure_ascii=False))
        print('result[send_normal_picking_data]: ', result)


def send_choice_picking_data(picking_batch_id):
    picking_batch_id = self.env['stock.picking.batch'].browse(picking_batch_id)

    loading_plan = picking_batch_id.send_vehicle_loading_plan_to_wms()

    data = []
    for index_i, picking_id in enumerate(picking_batch_id.picking_ids):
        # 发送带有装车计划的数据
        tmp = picking_batch_id._format_picking_data(picking_id)

        tmp.update({
            'vin': VIN_TEST[index_i]
        })
        data.append(tmp)

    post_data = {
        'picking_ids': data,
    }
    if loading_plan:
        post_data.update({
            'loading_plan': loading_plan
        })
    print('post_data: ', post_data)
    result = zeep_task_client.service.sendToTask(json.dumps(post_data, ensure_ascii=False))
    print('result[send_normal_picking_data]: ', result)


# 发送随机数据
def send_random_picking_data(loop_time):
    for _ in range(loop_time):
        all_picking_ids = self.env['stock.picking'].search([])
        all_picking_ids = self.env['stock.picking'].search([
            ('picking_type_id.name', 'like', '入库'),
            ('sale_order_line_id', '!=', False)
        ])
        picking_ids = [random.choice(all_picking_ids) for _ in range(random.randint(50, 100))]
        data = get_all_format_picking_data(picking_ids)
        post_data = {
            'picking_ids': data
        }
        result = zeep_task_client.service.sendToTask(json.dumps(post_data, ensure_ascii=False))
        print('result[send_random_picking_data]: ', result)


def send_partner_info(loop_time):
    partner_ids = self.env['res.partner'].search([])
    for _ in range(loop_time):
        # partner_ids = [random.choice(partner_ids) for _ in range(random.randint(300, 1200))]
        data = []
        for line_id in partner_ids:
            tmp = {}
            for key_id in SUPPLIER_FIELD_DICT.keys():
                if getattr(line_id, key_id):
                    key_value = getattr(line_id, key_id)
                    tmp.update({
                        SUPPLIER_FIELD_DICT.get(key_id): getattr(key_value, 'name') if hasattr(key_value,
                                                                                               'name') else key_value
                    })
            if tmp:
                data.append(tmp)
        result = zeep_supplier_client.service.supplier(str(data))
        print('result[send_partner_info]: ', result)


def send_search_stock_query(loop_time):
    order_line_ids = self.env['sale.order.line'].search([])
    for _ in range(loop_time):
        order_line_ids = [random.choice(order_line_ids) for _ in range(random.randint(10, 60))]
        data = []
        for line_id in order_line_ids:
            tmp = {
                'vin': line_id.vin_code,
                'product_id': line_id.product_id.display_name
            }
            data.append(tmp)
        if data:
            result = zeep_check_stock_client.service.searchInventory(str(data))
            print('result[send_search_stock_query]: ', result)


if __name__ == '__main__':
    # send_partner_info(1)
    send_choice_picking_data(56)
    # import time
    # while True:
    #
    #     send_normal_picking_data(1)
    #     send_random_picking_data(1)
    #     time.sleep(120)
    # loop_time = 10
    # for _ in range(loop_time):
    #     send_normal_picking_data(loop_time)
    #     send_random_picking_data(loop_time)
    #     send_partner_info(loop_time)
    #     send_search_stock_query(loop_time)

{
    'picking data': [{
        'task_id': 414,
        'product_name': '福睿斯',
        'product_color': False,
        'product_model': False,
        'product_config': False,
        'supplier_name': ' 天津市尊泰汽车销售服务有限公司',
        'warehouse_code': 'WTJCXBK',
        'quantity_done': 1,
        'brand_model_name': '长安福特',
        'from_location_id': 'WTJCXBK/团结村线边库/出库位置',
        'to_location_id': 'STJCZ/团结村站/装车位置',
        'partner_name': '长安民生',
        'vin': 'LL0001',
        'picking_type_name': '团结村线边库: 装车',
        'batch_id': 20
    }, {
        'task_id': 505,
        'product_name': '福睿斯',
        'product_color': False,
        'product_model': False,
        'product_config': False,
        'supplier_name': ' 天津市尊泰汽车销售服务有限公司',
        'warehouse_code': 'WTJCXBK',
        'quantity_done': 1,
        'brand_model_name': '长安福特',
        'from_location_id': 'WTJCXBK/团结村线边库/出库位置',
        'to_location_id': 'STJCZ/团结村站/装车位置',
        'partner_name': '长安民生',
        'vin': 'LVCT20001',
        'picking_type_name': '团结村线边库: 装车',
        'batch_id': 20
    }, {
        'task_id': 514,
        'product_name': '福睿斯',
        'product_color': False,
        'product_model': False,
        'product_config': False,
        'supplier_name': ' 天津市尊泰汽车销售服务有限公司',
        'warehouse_code': 'WTJCXBK',
        'quantity_done': 1,
        'brand_model_name': '长安福特',
        'from_location_id': 'WTJCXBK/团结村线边库/出库位置',
        'to_location_id': 'STJCZ/团结村站/装车位置',
        'partner_name': '长安民生',
        'vin': 'LVCT20002',
        'picking_type_name': '团结村线边库: 装车',
        'batch_id': 20
    }, {
        'task_id': 523,
        'product_name': '福睿斯',
        'product_color': False,
        'product_model': False,
        'product_config': False,
        'supplier_name': ' 天津市尊泰汽车销售服务有限公司',
        'warehouse_code': 'WTJCXBK',
        'quantity_done': 1,
        'brand_model_name': '长安福特',
        'from_location_id': 'WTJCXBK/团结村线边库/出库位置',
        'to_location_id': 'STJCZ/团结村站/装车位置',
        'partner_name': '长安民生',
        'vin': 'LVCT20003',
        'picking_type_name': '团结村线边库: 装车',
        'batch_id': 20
    }, {
        'task_id': 576,
        'product_name': '福睿斯',
        'product_color': False,
        'product_model': False,
        'product_config': False,
        'supplier_name': ' 天津市尊泰汽车销售服务有限公司',
        'warehouse_code': 'WTJZXBK',
        'quantity_done': 1,
        'brand_model_name': '长安福特',
        'from_location_id': 'WTJZXBK/唐家沱线边库/出库位置',
        'to_location_id': 'STJZZ/唐家沱站/装车位置',
        'partner_name': '长安民生',
        'vin': 'DY0002',
        'picking_type_name': '唐家沱线边库: 装车',
        'batch_id': 20
    }]
}

