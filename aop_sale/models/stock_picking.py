# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    origin_purchase_id = fields.Many2one('purchase.order', 'Origin purchase order', copy=False)
    delivery_to_partner_id = fields.Many2one('res.partner', 'Delivery to partner', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Order line', copy=False)
    handover_number = fields.Char('Handover number')

    vin_id = fields.Many2one('stock.production.lot', string='VIN')
    picking_incoming_number = fields.Integer('Picking incoming number')
    is_must_mount_car = fields.Boolean(string='Is must mount car', default=False)

    real_stock_location_id = fields.Many2one('stock.location', 'Real stock location')

    product_id = fields.Many2one(
        'product.product',
        'Product',
        related='move_lines.product_id',
        readonly=False,
        store=True
    )

    delivery_carrier_id = fields.Many2one('delivery.carrier', 'Delivery carrier')
    # route_id = fields.Many2one('stock.location.route', related='delivery_carrier_id.route_id', store=True)
    route_id = fields.Many2one('stock.location.route', related='sale_order_line_id.route_id', store=True)

    def match_sale_order(self):
        return self._match_sale_order()

    # 根据产品，vin ，匹配订单
    def _match_sale_order(self):
        order_line_id = self.env['sale.order.line']

        for move_line in self.move_lines:
            match_domain = [
                ('product_id', '=', move_line.product_id.id),
                ('vin_code', 'in', move_line.move_line_ids.mapped('lot_id').mapped('name')),
                ('order_id.state', '=', 'draft')
            ]
            order_id = order_line_id.search(match_domain).mapped('order_id') if order_line_id.search(
                match_domain) else False

            if not order_id:
                raise UserError('There have not order exist.')

            # FIXME: order_id 应该是一个才对
            for order in order_id:
                order.action_confirm()

    @api.multi
    def button_validate(self):
        for picking_id in self:
            self._fill_serial_no(picking_id)
        res = super(StockPicking, self).button_validate()
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

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self.env['ir.rule'].clear_cache()
        return super(StockPicking, self).search_read(domain, fields, offset, limit, order)
