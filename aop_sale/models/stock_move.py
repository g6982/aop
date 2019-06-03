# -*_ coding :utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _merge_moves(self, merge_into=False):
        res = super(StockMove, self)._merge_moves(merge_into=merge_into)
        picking_ids = self.mapped('picking_id')
        for picking_id in picking_ids:
            if not picking_id.picking_purchase_id:
                picking_id.create_purchase_order()
        return res

    def _search_picking_for_assignation(self):
        if self._context.get('do_not_merge'):
            return False
        else:
            return super(StockMove, self)._search_picking_for_assignation()

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        vals['move_id_without_package'] = self.id
        return vals

    def _prepare_procurement_values(self):
        values = super(StockMove, self)._prepare_procurement_values()

        if self.sale_line_id:
            values.update({'sale_line_id': self.sale_line_id.id})

        return values