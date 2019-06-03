# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons import decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    src_partner_id = fields.Many2one('res.partner', related='picking_type_id.src_partner_id')
    des_partner_id = fields.Many2one('res.partner', related='picking_type_id.des_partner_id')

    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase')

    move_id_without_package = fields.Many2one('stock.move', string="库存移动",
                                               domain=['|', ('package_level_id', '=', False),
                                                       ('picking_type_entire_packs', '=', False)])

    product_id = fields.Many2one(string='Product', related='move_id_without_package.product_id')

    vin = fields.Many2one(string='vin', related='move_id_without_package.move_line_ids.lot_id')

    product_uom_qty = fields.Float(
        '初始数量',
        related='move_id_without_package.product_uom_qty')

    quantity_done = fields.Float('完成数量', related='move_id_without_package.quantity_done')



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
        vendor = self._get_vendor_partner()
        res = {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': vendor[0],
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_id': self.id
        }
        line_data = self._get_purchase_line_data()
        res.update({
            'order_line': line_data
        })
        return res

    def _get_vendor_partner(self):
        vendors = []
        for line_id in self.move_ids_without_package:
            if not line_id.product_id.seller_ids:
                raise UserError(u'请先给产品 [ {} ] 指定供应商!'.format(
                    line_id.product_id.name
                ))
            _logger.info({
                '=' * 50: line_id.product_id.seller_ids
            })
            vendors.append(line_id.product_id.seller_ids[0].name.id)
        if len(list(set(vendors))) > 1:
            raise UserError(u'存在多个供应商! ')
        _logger.info({
            '*' * 100: vendors
        })
        return list(set(vendors))

    def _get_purchase_line_data(self):
        res = []
        for line_id in self.move_ids_without_package:
            res.append((0, 0, {
                'product_id': line_id.product_id.id,
                'service_product_id': self.picking_type_id.product_id.id,
                'product_qty': line_id.product_uom_qty,
                'name': line_id.product_id.name,
                'date_planned': fields.Datetime.now(),
                'price_unit': line_id.product_id.lst_price,
                'product_uom': line_id.product_id.uom_id.id
            }))
        return res


