# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ChangeStockPicking(models.TransientModel):
    _name = 'change.stock.picking.wizard'

    picking_id = fields.Many2many('stock.picking')

    line_ids = fields.One2many('change.stock.picking.line.wizard', 'change_wizard_id')

    @api.model
    def default_get(self, fields):
        res = super(ChangeStockPicking, self).default_get(fields)
        ids = self._context.get('active_ids', [])

        if ids:
            res['picking_id'] = [(6, 0, ids)]
        return res

    def dispatch_stock_picking(self):
        pass


class ChangeStockPickingLine(models.TransientModel):
    _name = 'change.stock.picking.line.wizard'

    from_location = fields.Many2one('stock.location')
    to_location = fields.Many2one('stock.location')

    change_wizard_id = fields.Many2one('change.stock.picking.wizard')
