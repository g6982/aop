# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    src_partner_id = fields.Many2one('res.partner', string='Src partner')
    des_partner_id = fields.Many2one('res.partner', string='Des partner')

    product_id = fields.Many2one('product.product')

    aging = fields.Float('时效', default=1)

