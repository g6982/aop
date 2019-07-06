# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    service_product_id = fields.Many2one('product.product', string='Service product',
                                         related='picking_type_id.service_product_id')
    aging = fields.Float('Aging(day)', default=1)
    package_product_id = fields.Many2one('product.product', 'Package product')

    # 添加服务产品到stock.picking
    def _get_custom_move_fields(self):
        res = super(StockRule, self)._get_custom_move_fields()
        res += ['service_product_id', 'vin_id']
        return res

    # 获取库存产品的位置
    def _get_product_stock_location(self, product_id, vin_id):
        stock_quant_id = self.env['stock.quant'].search([
            ('product_id', '=', product_id.id),
            ('lot_id', '=', vin_id),
            ('quantity', '>', 0),
            ('reserved_quantity', '=', 0),
            ('location_id.usage', '=', 'internal')
        ]) if vin_id else False
        return stock_quant_id.location_id.id if stock_quant_id else False

    def _run_pull(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        product_stock_id = self._get_product_stock_location(product_id, values.get('vin_id', False))
        if location_id.id == product_stock_id if product_stock_id else False:
            return True
        res = super(StockRule, self)._run_pull(product_id, product_qty, product_uom, location_id, name, origin, values)
        return res
