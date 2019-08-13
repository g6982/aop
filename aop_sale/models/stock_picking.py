# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    origin_purchase_id = fields.Many2one('purchase.order', 'Origin purchase order', copy=False)
    delivery_to_partner_id = fields.Many2one('res.partner', 'Delivery to partner', readonly=True)

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

            # FIXME: order_id 应该是一个才对
            for order in order_id:
                order.action_confirm()

            if not order_id:
                raise UserError('There have not order exist.')

    @api.multi
    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        self.sudo()._validate_origin_order()
        return res

    # 回溯原单据
    def _validate_origin_order(self):
        if self.origin_purchase_id.mapped('stock_picking_batch_id') if self.origin_purchase_id else False:
            for picking_id in self.origin_purchase_id.mapped('stock_picking_batch_id').sudo().picking_ids:
                self.sudo()._fill_serial_no(picking_id)
                picking_id.sudo().action_assign()
                picking_id.sudo().button_validate()
            self.origin_purchase_id.mapped('stock_picking_batch_id').done()

    # 填充批次号
    def _fill_serial_no(self, picking_id):
        for move_id in picking_id.move_lines:
            for line in move_id.move_line_ids:
                line.write({
                    'lot_id': move_id.vin_id.id,
                    'qty_done': line.product_uom_qty
                })
