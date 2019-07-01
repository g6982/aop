# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    service_product_id = fields.Many2one('product.product', string='Service Product')
    vin_id = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    def _prepare_procurement_values(self):
        res = super(StockMove, self)._prepare_procurement_values()
        res.update({
            'service_product_id': self.service_product_id.id,
            'vin_id': self.vin_id.id
        })
        return res

    # 获取库存产品的位置
    def _get_product_stock_location(self, product_id, vin_id):
        if not vin_id:
            return False
        stock_quant_id = self.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('lot_id', '=', vin_id.id),
            ('quantity', '>', 0),
            ('reserved_quantity', '=', 0),
            ('location_id.usage', '=', 'internal')
        ])
        return stock_quant_id.location_id.id if stock_quant_id else False

    def _assign_picking_post_process(self, new=False):
        res = super(StockMove, self)._assign_picking_post_process(new)
        stock_location_id = self._get_product_stock_location(self.product_id.id, self.vin_id)
        if stock_location_id == self.location_id.id:
            # self._action_confirm()
            # self._action_assign()
            # self.state = 'assigned'
            # 如果存在库存，从库存中获取，这样不依赖于其他的规则
            self.procure_method = 'make_to_stock'
            # self.picking_id.state = 'assigned'
            self.picking_id.action_assign()
        return res
