# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # car_no_ids = fields.Many2many('stock.quant.package', string='Loading number')

    partner_id = fields.Many2one('res.partner', string='Vendor')
    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase')
    dispatch_type = fields.Selection([('center_type', 'Center'),
                                      ('train_type', 'train'),
                                      ('highway_type', 'highway')
                                      ],
                                     string='Dispatch type',
                                     store=True)
    plan_number = fields.Integer(string='Plan number', default=1)

    vehicle_number = fields.Char(string='Vehicle number')

    mount_car_plan_ids = fields.One2many('mount.car.plan', 'stock_picking_batch_id', string='Mount plan')



    def create_purchase_order(self):
        try:
            data = self._get_purchase_data()
            res = self.env['purchase.order'].create(data)

            self.write({
                'picking_purchase_id': res.id
            })
        except Exception as e:
            self._cr.rollback()
            raise UserError(e)

    def _get_purchase_data(self):
        vendor = self.partner_id.id
        res = {
            'partner_id': vendor,
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_batch_id': self.id
        }
        line_data = self._get_purchase_line_data()
        res.update({
            'order_line': line_data
        })
        return res

    def _get_purchase_line_data(self):
        res = []

        product_ids = []

        for picking in self.picking_ids:
            for line_id in picking.move_ids_without_package:
                data = {
                    'product_id': line_id.product_id.id,
                    # 'service_product_id': line_id.picking_type_id.product_id.id,
                    'product_qty': line_id.product_uom_qty,
                    'name': line_id.product_id.name,
                    'date_planned': fields.Datetime.now(),
                    'price_unit': line_id.product_id.lst_price,
                    'product_uom': line_id.product_id.uom_id.id
                }

                if not data['product_id'] in product_ids:
                    product_ids.append(data['product_id'])
                    res.append((0, 0, data))
        return res


class MountCarPlan(models.Model):
    _name = "mount.car.plan"

    name = fields.Char(string='Vehicle model')

    layer_option = fields.Selection([
        ('upper_layer', 'Upper layer'),
        ('lower_layer', 'Lower layer')
    ], string='Layer')

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Dispatch order')