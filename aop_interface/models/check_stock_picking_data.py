# -*- coding: utf-8 -*-

from odoo import fields, models


class CheckStockPicking(models.Model):
    _name = 'check.stock.picking.log'

    name = fields.Char('Name')

    state = fields.Boolean('State')
    partner_id = fields.Char('Partner')
    product_id = fields.Char('Product')
    vin = fields.Char('VIN')
    from_location_id = fields.Char('From location')
    to_location_id = fields.Char('To location')