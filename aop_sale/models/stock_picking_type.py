# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    service_product_id = fields.Many2one('product.product', 'Service product')
