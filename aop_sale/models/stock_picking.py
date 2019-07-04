# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def match_sale_order(self):
        return self._match_sale_order()

    # 根据产品，vin ，匹配订单
    def _match_sale_order(self):
        order_line_id = self.env['sale.order.line']

        for move_line in self.move_lines:
            match_domain = [
                ('product_id', '=', move_line.product_id.id),
                ('vin', 'in', move_line.move_line_ids.mapped('lot_id').ids),
                ('order_id.state', '=', 'draft')
            ]
            order_id = order_line_id.search(match_domain).mapped('order_id') if order_line_id.search(
                match_domain) else False

            # TODO: FIX Later, order_id 应该是一个才对
            for order in order_id:
                order.action_confirm()

            if not order_id:
                raise UserError('There have not order exist.')
