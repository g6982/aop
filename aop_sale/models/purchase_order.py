# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Stock batch')

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({
            'origin_purchase_id': self.id
        })
        return res

    # 完成的同时，完成 batch
    @api.multi
    def button_confirm(self):
        try:
            # 服务产品
            res = super(PurchaseOrder, self).button_confirm()
            _logger.info({
                'hello': self.mapped('order_line').mapped('product_id').mapped('type')
            })
            if 'service' in self.mapped('order_line').mapped('product_id').mapped('type'):
                for order_id in self:
                    for picking_id in order_id.mapped('stock_picking_batch_id').picking_ids:
                        self._fill_serial_no(picking_id)
                        picking_id.action_assign()
                        picking_id.button_validate()
                    order_id.mapped('stock_picking_batch_id').done()
            return res
        except Exception as e:
            import traceback
            raise UserError(traceback.format_exc())
            self._cr.rollback()
            res = super(PurchaseOrder, self).button_confirm()
            return res

    # 填充批次号
    def _fill_serial_no(self, picking_id):
        for move_id in picking_id.move_lines:
            for line in move_id.move_line_ids:
                line.write({
                    'lot_id': move_id.vin_id.id,
                    'qty_done': line.product_uom_qty
                })
