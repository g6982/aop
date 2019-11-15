# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    service_product_id = fields.Many2one('product.product', 'Service product')

    limit_picking_batch = fields.Boolean('Limit picking batch', default=False)

    code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')
    ], 'Type of Operation', required=True, default='internal')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self.env['ir.rule'].clear_cache()
        return super(StockPickingType, self).search_read(domain, fields, offset, limit, order)