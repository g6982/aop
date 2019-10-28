# -*- coding: utf-8 -*-

from odoo import fields, models


class DonePicking(models.Model):
    _name = 'done.picking.log'

    name = fields.Char('Name')

    state = fields.Boolean('State')
    partner_id = fields.Char('Partner')
    product_id = fields.Char('Product')
    vin = fields.Char('VIN')
    from_location_id = fields.Char('From location')
    to_location_id = fields.Char('To location')
    picking_type_id = fields.Char('Picking type')
    quantity_done = fields.Integer('quantity')
