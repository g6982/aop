# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
import time
from itertools import groupby
from odoo.exceptions import UserError
from ..tools.zeep_client import zeep_task_client
_logger = logging.getLogger(__name__)
import json

PICKING_FIELD_DICT = {
    'partner_id': 'partner_name',
    'vin_id': 'vin',
    'picking_type_id': 'picking_type_name',
}


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # car_no_ids = fields.Many2many('stock.quant.package', string='Loading number')

    un_limit_partner_id = fields.Many2one('res.partner', string='Vendor')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    allow_partner_ids = fields.Many2many('res.partner',
                                         string='Allow partners',
                                         store=True,
                                         compute='_compute_allow_partner_ids')
    limit_state = fields.Selection([
        ('limit', 'Limit'),
        ('un_limit', 'Un-limit')
    ], dafault='un_limit')

    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase', copy=False)
    dispatch_type = fields.Selection([('center_type', 'Center'),
                                      ('train_type', 'train'),
                                      ('highway_type', 'highway')
                                      ],
                                     string='Dispatch type',
                                     store=True)
    plan_number = fields.Integer(string='Plan number', default=1)

    vehicle_number = fields.Char(string='Vehicle number')

    mount_car_plan_ids = fields.One2many('mount.car.plan', 'stock_picking_batch_id', string='Mount plan')

    transfer_partner_id = fields.Many2one('res.partner', 'Transfer company')

    # WMS 任务信息
    def _format_picking_data(self, picking_id):
        '''
        :param picking_id: 任务
        :return: 任务所包含的信息，传送给WMS
        '''
        product_info = picking_id.sale_order_line_id.product_model
        tmp = {
            'task_id': picking_id.id,
            'product_name': picking_id.sale_order_line_id.product_id.name,
            'product_color': picking_id.sale_order_line_id.product_color,
            'product_model': product_info[:3] if product_info else False,
            'product_config': product_info[3:] if product_info else False,
            'supplier_name': self.un_limit_partner_id.name if self.un_limit_partner_id else self.partner_id.name,
            'warehouse_code': picking_id.picking_type_id.warehouse_id.code,
            'quantity_done': 1,
            'brand_model_name': picking_id.sale_order_line_id.product_id.brand_id.name,
            'from_location_id': picking_id.location_id.display_name,
            'to_location_id': picking_id.location_dest_id.display_name,
            'to_location_type': picking_id.location_dest_id.usage
        }
        for key_id in PICKING_FIELD_DICT.keys():
            if getattr(picking_id, key_id) if hasattr(picking_id, key_id) else False:
                key_value = getattr(picking_id, key_id)
                tmp.update({
                    PICKING_FIELD_DICT.get(key_id): getattr(key_value, 'name') if hasattr(key_value,
                                                                                          'name') else key_value
                })
        return tmp

    # 接口。创建采购单后，发送任务数据到WMS
    def send_to_wms_data(self):
        data = []
        for picking_id in self.picking_ids:
            # 接车并不需要发送到WMS
            if picking_id.picking_incoming_number > 0 or not picking_id.sale_order_line_id:
                continue
            tmp = self._format_picking_data(picking_id)
            data.append(tmp)
        _logger.info({
            'picking data': data
        })

        loading_plan = self.send_vehicle_loading_plan_to_wms()

        post_data = {
            'picking_ids': data
        }
        if loading_plan:
            post_data.update({
                'loading_plan': loading_plan
            })
        _logger.info({
            'post_data': post_data
        })
        if post_data:
            # 输出中文
            zeep_task_client.service.sendToTask(json.dumps(post_data, ensure_ascii=False))

    def send_vehicle_loading_plan_to_wms(self):
        data = []
        for line_id in self.mount_car_plan_ids:
            tmp = {
                'transfer_tool_number': line_id.transfer_tool_number,
                'product_model': line_id.name.default_code,
                'product_model_layer': line_id.layer_option,
                'product_model_number': line_id.number,
                'transfer_company_name': self.transfer_partner_id.name
            }
            data.append(tmp)
        return data

    # 生成采购订单，采购：服务产品
    def create_purchase_order(self):
        try:
            data, service_product_context = self._get_purchase_data()

            if service_product_context:
                return {
                    'name': _(u'测试'),
                    'view_type': 'form',
                    "view_mode": 'form',
                    'res_model': 'fill.service.product.wizard',
                    'type': 'ir.actions.act_window',
                    'context': service_product_context,
                    'target': 'new',
                }

            # 跨公司创建
            res = self.env['purchase.order'].sudo().create(data)

            # 接口数据
            self.send_to_wms_data()

            self.write({
                'picking_purchase_id': res.id
            })
        except Exception as e:
            self._cr.rollback()
            import traceback
            raise UserError(traceback.format_exc())

    # 根据条件。获取值
    def get_vendor_id(self):
        if self.limit_state == 'limit' and self.allow_partner_ids:
            return self.partner_id.id if self.partner_id else self.un_limit_partner_id.id
        else:
            return self.un_limit_partner_id.id if self.un_limit_partner_id else self.partner_id.id

    # 跨公司生成采购订单，对应的客户，即是对应公司的客户
    def _get_purchase_data(self):
        vendor = self.get_vendor_id()
        if not vendor:
            raise UserError('You must check selection records.')

        res = {
            'name': str(time.time()),
            'partner_id': vendor,
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_batch_id': self.id,
            # 'company_id': self._match_company_id(self.partner_id)
            'company_id': self.env.user.company_id.id
        }

        data = self._get_purchase_line_data()
        line_data, lost_service_product_id = data[0], data[-1]

        service_product_context = []
        if lost_service_product_id:
            service_product_context = {
                'default_stock_picking_batch_id': self.id,
                'default_wizard_line_ids': [(0, 0, {
                    'picking_id': line.id,
                    'from_location_id': line.location_id.id,
                    'to_location_id': line.location_dest_id.id
                }) for line in lost_service_product_id],
            }
        res.update({
            'order_line': line_data
        })
        return res, service_product_context

    # 服务产品
    # 产品不能添加公司属性值
    def _get_purchase_line_data(self):
        res = []

        lost_service_product_id = []

        for picking in self.picking_ids:
            for _ in range(picking.picking_incoming_number) if picking.picking_incoming_number > 1 else []:
                res, lost_service_product_id = self._parse_purchase_line_data(picking, lost_service_product_id, res)
            if picking.picking_incoming_number <= 1:
                res, lost_service_product_id = self._parse_purchase_line_data(picking, lost_service_product_id, res)

        return [res, lost_service_product_id]

    def _parse_purchase_line_data(self, picking, lost_service_product_id, res):
        carrier_id = self._parse_service_product_supplier(picking)

        service_product_id = carrier_id.service_product_id if carrier_id else False

        if not service_product_id:
            lost_service_product_id.append(picking)

        for line_id in picking.move_lines:
            data = {
                'product_id': service_product_id.id if service_product_id else line_id.picking_type_id.service_product_id.id if line_id.picking_type_id.service_product_id else False,
                'transfer_product_id': line_id.product_id.id,
                # 'service_product_id': service_product_id.id if service_product_id else False,
                'product_qty': line_id.product_uom_qty,
                'sale_line_id': line_id.sale_order_line_id.id,
                'name': picking.picking_type_id.display_name,
                'date_planned': fields.Datetime.now(),
                'service_contract_price': carrier_id.product_standard_price if carrier_id else 0,
                'price_unit': 0,
                'product_uom': service_product_id.uom_id.id if service_product_id else line_id.picking_type_id.service_product_id.uom_id.id if line_id.picking_type_id.service_product_id else False,
                'batch_stock_picking_id': picking.id,
                'vin_code': line_id.vin_id.name if line_id.vin_id else False
            }
            res.append((0, 0, data))
        if not picking.move_lines and service_product_id:
            data = {
                'product_id': service_product_id.id,
                'product_qty': 1,
                'name': service_product_id.name,
                'product_uom': service_product_id.uom_id.id,
                'batch_stock_picking_id': picking.id,
                'carrier_id.product_standard_price if carrier_id else ': carrier_id.product_standard_price,
                'price_unit': 0,
                'date_planned': fields.Datetime.now(),
            }
            res.append((0, 0, data))
        lost_service_product_id = list(set(lost_service_product_id))
        return res, lost_service_product_id

    # 查找供应商合同条款
    def _parse_service_product_supplier(self, picking):
        contract_domain = [
            ('supplier_contract_id.partner_id', '=', self.partner_id.id),
            ('from_location_id', '=', picking.location_id.id),
            ('to_location_id', '=', picking.location_dest_id.id)
        ]
        delivery_carrier_id = self.env['delivery.carrier'].search(contract_domain)
        return delivery_carrier_id[0] if delivery_carrier_id else False

    def _match_company_id(self, partner_id):
        res = self.env['res.company'].sudo().search([('code', '=', partner_id.ref)])
        return res.id if res else False

    @api.multi
    @api.depends('picking_ids')
    def _compute_allow_partner_ids(self):
        # self.ensure_one()
        for line in self:
            picking_ids = line.mapped('picking_ids')

            # 搜索客户合同
            customer_contract_id = self.env['customer.aop.contract'].search([
                ('partner_id', 'in', list(set(picking_ids.mapped('partner_id').ids)))
            ])

            # 根据任务和客户和同，过滤供应商合同
            partner_ids = self.find_supplier_contract_partner(picking_ids, customer_contract_id=customer_contract_id)
            if not partner_ids:
                line.allow_partner_ids = False
                line.limit_state = 'un_limit'
            else:
                line.allow_partner_ids = [(6, 0, partner_ids)]
                line.limit_state = 'limit'

    # 任务
    # 判断 来源和目的地 以及步骤
    def find_supplier_contract_partner(self, picking_ids, customer_contract_id=False):
        '''
        :param picking_ids: 任务集
        :param customer_contract_id: 客户合同
        :return: 允许的供应商
        '''
        data = []
        location_ids = picking_ids.mapped('location_id')
        location_dest_ids = picking_ids.mapped('location_dest_id')
        picking_type_ids = picking_ids.mapped('picking_type_id')

        carrier_ids = self.env['delivery.carrier'].search([
            ('from_location_id', 'in', location_ids.ids),
            ('to_location_id', 'in', location_dest_ids.ids),
            ('picking_type_id', 'in', picking_type_ids.ids),
        ])
        picking_set_data = self._parse_from_to_picking_type_ids(picking_ids=picking_ids)

        # 对合同交款，按照供应商合同进行分组， 然后组成条件的集合
        for supplier_contract_id, delivery_carrier_ids in groupby(carrier_ids, lambda x: x.supplier_contract_id):
            carrier_set_data = self._parse_from_to_picking_type_ids(carrier_ids=delivery_carrier_ids)

            if picking_set_data - carrier_set_data:
                continue

            # 如果勾选了允许的客户合同，做一次过滤
            if customer_contract_id and supplier_contract_id.mapped('allow_customer_contract_ids'):
                # 交集
                if not set(customer_contract_id.ids) & set(supplier_contract_id.mapped('allow_customer_contract_ids').ids):
                    continue
            data.append(supplier_contract_id.partner_id.id)

        return data

    # 组成集合
    def _parse_from_to_picking_type_ids(self, picking_ids=False, carrier_ids=False):
        '''
        :param picking_ids: 批量调度选择的任务
        :param carrier_ids: 合同交款
        :return: 条件的集合{(x1,x2,x3), (x4,x5,x6)}
        '''
        data = []
        if carrier_ids:
            for carrier_id in carrier_ids:
                data.append(
                    (carrier_id.from_location_id.id, carrier_id.to_location_id.id, carrier_id.picking_type_id.id)
                )
        elif picking_ids:
            for picking_id in picking_ids:
                data.append(
                    (picking_id.location_id.id, picking_id.location_dest_id.id, picking_id.picking_type_id.id)
                )
        return set(data)


class MountCarPlan(models.Model):
    _name = "mount.car.plan"

    # name = fields.Char(string='Vehicle model')

    name = fields.Many2one('product.product', string='Vehicle model', domain=[('type', '=', 'product')])

    transfer_tool_number = fields.Char('Transfer tool no')
    layer_option = fields.Selection([
        ('upper_layer', 'Upper layer'),
        ('lower_layer', 'Lower layer')
    ], string='Layer')

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Dispatch order')

    number = fields.Integer('Number')
