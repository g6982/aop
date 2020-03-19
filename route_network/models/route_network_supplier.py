#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
import logging


_logger = logging.getLogger(__name__)


class RouteNetworkVendor(models.Model):
    _name = 'route.network.vendor'

    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Supplier')

    line_ids = fields.One2many('route.network.delivery', 'vendor_id', string='Line')


class RouteNetworkDelivery(models.Model):
    _name = 'route.network.delivery'

    vendor_id = fields.Many2one('route.network.vendor')
    from_location_id = fields.Many2one('stock.location', string='From')
    to_location_id = fields.Many2one('stock.location', string='To')
    unit_price = fields.Float('Price', digits=dp.get_precision('Price of delivery'))
