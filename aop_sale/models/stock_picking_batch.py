# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # car_no_ids = fields.Many2many('stock.quant.package', string='Loading number')

    partner_id = fields.Many2one('res.partner', string='Vendor')
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

    # 生成采购订单，采购：服务产品
    def create_purchase_order(self):
        try:
            data = self._get_purchase_data()

            # 跨公司创建
            res = self.env['purchase.order'].sudo().create(data)

            self.write({
                'picking_purchase_id': res.id
            })
        except Exception as e:
            self._cr.rollback()
            raise UserError(e)

    # 跨公司生成采购订单，对应的客户，即是对应公司的客户
    def _get_purchase_data(self):
        vendor = self.partner_id.id
        res = {
            'name': str(time.time()),
            'partner_id': vendor,
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_batch_id': self.id,
            'company_id': self._match_company_id(self.partner_id)
        }
        line_data = self._get_purchase_line_data()
        res.update({
            'order_line': line_data
        })
        return res

    # 服务产品
    # 产品不能添加公司属性值
    def _get_purchase_line_data(self):
        res = []

        product_ids = []

        for picking in self.picking_ids:
            for line_id in picking.move_lines:
                data = {
                    'product_id': line_id.service_product_id.id,
                    'transfer_product_id': line_id.product_id.id,
                    # 'service_product_id': line_id.picking_type_id.product_id.id,
                    'product_qty': line_id.product_uom_qty,
                    'name': line_id.service_product_id.name,
                    'date_planned': fields.Datetime.now(),
                    'price_unit': line_id.service_product_id.lst_price,
                    'product_uom': line_id.service_product_id.uom_id.id
                }
                res.append((0, 0, data))
                # if not data['product_id'] in product_ids:
                #     product_ids.append(data['product_id'])
                #     res.append((0, 0, data))
        return res

    def _match_company_id(self, partner_id):
        res = self.env['res.company'].sudo().search([('code', '=', partner_id.ref)])
        return res.id if res else False


class MountCarPlan(models.Model):
    _name = "mount.car.plan"

    name = fields.Char(string='Vehicle model')

    layer_option = fields.Selection([
        ('upper_layer', 'Upper layer'),
        ('lower_layer', 'Lower layer')
    ], string='Layer')

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Dispatch order')