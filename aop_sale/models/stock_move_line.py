# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_id = vals.get('move_id')

            stock_move = self.env['stock.move'].search([
                ('id', '=', move_id)
            ], limit=1)

            if stock_move.sale_line_id and stock_move.sale_line_id.vin:
                vals.update({'lot_id': stock_move.sale_line_id.vin.id})

        return super(StockMoveLine, self).create(vals_list)
