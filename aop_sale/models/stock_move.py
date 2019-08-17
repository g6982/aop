# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    service_product_id = fields.Many2one('product.product', string='Service Product')
    delivery_carrier_id = fields.Many2one('delivery.carrier', 'Delivery carrier')
    vin_id = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    delivery_to_partner_id = fields.Many2one('res.partner', 'Delivery to partner', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Order Line', readonly=True)

    def _prepare_procurement_values(self):
        res = super(StockMove, self)._prepare_procurement_values()
        res.update({
            # 'service_product_id': self.service_product_id.id,
            'service_product_id': self._get_service_product_id(self.delivery_carrier_id, self.rule_id),
            'vin_id': self.vin_id.id,
            'delivery_carrier_id': self.delivery_carrier_id.id,
            'delivery_to_partner_id': self.delivery_to_partner_id.id,
            'sale_order_line_id': self.sale_order_line_id.id
        })
        return res

    # 使用条款对应的服务产品
    def _get_service_product_id(self, delivery_carrier_id, rule_id):
        rule_ids = delivery_carrier_id.mapped('rule_service_product_ids')

        rule_id = rule_ids.filtered(lambda x: x.rule_id == rule_id)
        if not rule_id:
            return False
        return rule_id.service_product_id.id if rule_id.service_product_id else False

    # 获取库存产品的位置
    def _get_product_stock_location(self, product_id, vin_id):
        if not vin_id:
            return False
        stock_quant_id = self.env['stock.quant'].sudo().search([
            ('product_id', '=', product_id),
            ('lot_id', '=', vin_id.id),
            ('quantity', '>', 0),
            ('reserved_quantity', '=', 0),
            ('location_id.usage', '=', 'internal')
        ])
        # _logger.info({
        #     'stock_quant_id': stock_quant_id
        # })
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

        update_ids = self.sale_order_line_id.stock_picking_ids.ids + [self.picking_id.id]
        self.sale_order_line_id.write({
            'stock_picking_ids': [(6, 0, list(set(update_ids)))]
        })

        if self.picking_id.id not in self.sale_order_line_id.order_id.picking_ids.ids:
            self.sale_order_line_id.order_id.write({
                'picking_ids': [(4, self.picking_id.id)]
            })

        return res

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        res.update({
            'delivery_to_partner_id': self.delivery_to_partner_id.id,
            'sale_order_line_id': self.sale_order_line_id.id
        })
        return res

    def _search_picking_for_assignation(self):
        res = super(StockMove, self)._search_picking_for_assignation()
        return False

    # 重写该方法
    # 预留使用已存在的vin_id
    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Create or update move lines.
        """
        self.ensure_one()

        # FIXME: 重写该方法，使用 stock.move ，即sale.order.line 传过来的lot_id/vin_id
        if not lot_id:
            lot_id = self.env['stock.production.lot']

        if hasattr(self, 'vin_id'):
            lot_id = self.vin_id
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        # `taken_quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `taken_quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []

        if self.product_id.tracking == 'serial':
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                quants = self.env['stock.quant']._update_reserved_quantity(
                    self.product_id, location_id, taken_quantity, lot_id=lot_id,
                    package_id=package_id, owner_id=owner_id, strict=strict
                )
        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = self.move_line_ids.filtered(lambda m: m.product_id.tracking != 'serial' and
                                                    m.location_id.id == reserved_quant.location_id.id and m.lot_id.id == reserved_quant.lot_id.id and m.package_id.id == reserved_quant.package_id.id and m.owner_id.id == reserved_quant.owner_id.id)
            if to_update:
                to_update[0].with_context(bypass_reservation_update=True).product_uom_qty += self.product_id.uom_id._compute_quantity(quantity, to_update[0].product_uom_id, rounding_method='HALF-UP')
            else:
                if self.product_id.tracking == 'serial':
                    for i in range(0, int(quantity)):
                        self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant))
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity