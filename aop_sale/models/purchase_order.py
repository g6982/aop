# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    stock_picking_id = fields.Many2one('stock.picking')

    stock_picking_batch_id = fields.Many2one('stock.picking.batch')
