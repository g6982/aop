# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ChangeSaleOrderLineRouteHistory(models.Model):
    _name = 'change.sale.order.line.route.history'

    name = fields.Char('Name')
    md5_name = fields.Char('MD5 name')
    line_ids = fields.One2many('change.sale.order.line.route.history.line', 'change_history_id', string='Line ids')


class ChangeSaleOrderLineRouteHistoryLine(models.Model):
    _name = 'change.sale.order.line.route.history.line'

    name = fields.Char('Name')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking type')
    from_location_id = fields.Many2one('stock.location', string='From')
    to_location_id = fields.Many2one('stock.location', string='To')

    change_history_id = fields.Many2one('change.sale.order.line.route.history')
