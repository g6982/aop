# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    vin = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    service_product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)],
                                         ondelete='restrict')

    # 新增 服务产品
    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        res.update({
            'service_product_id': self.service_product_id.id
        })
        return res
