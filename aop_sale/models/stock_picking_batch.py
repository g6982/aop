# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import traceback
import logging

_logger = logging.getLogger(__name__)



class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    car_no = fields.Char(string='车次号')

    partner_id = fields.Many2one('res.partner', string='Vendor')

    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase')


    def create_purchase_order(self):
        data = self._get_purchase_data()
        _logger.info({
            'data': data
        })
        res = self.env['purchase.order'].create(data)

        self.write({
            'picking_purchase_id': res.id
        })

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
                    #'service_product_id': line_id.picking_type_id.product_id.id,
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
