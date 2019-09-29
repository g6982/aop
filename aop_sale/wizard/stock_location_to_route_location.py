# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import random

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockLocationToRouteLocation(models.TransientModel):
    _name = 'stock.location.to.route.location.wizard'

    sale_order_id = fields.Many2one('sale.order')
    line_ids = fields.One2many('stock.location.to.route.location.line', 'line_id')

    def dispatch_order(self):
        pass


class StockLocationToRouteLocationLine(models.TransientModel):
    _name = 'stock.location.to.route.location.line'

    line_id = fields.Many2one('stock.location.to.route.location.wizard')

    sale_order_line_id = fields.Many2one('sale.order.line')
    vin_id = fields.Many2one('stock.production.lot')
    stock_location_id = fields.Many2one('stock.location')
    to_location_id = fields.Many2one('stock.location')
    route_id = fields.Many2one('stock.location.route')
    allowed_to_location_ids = fields.Many2many('stock.location')
