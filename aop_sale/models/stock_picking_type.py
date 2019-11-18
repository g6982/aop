# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    service_product_id = fields.Many2one('product.product', 'Service product')

    limit_picking_batch = fields.Boolean('Limit picking batch', default=False)

    import_name = fields.Char('Import name', compute='_compute_import_name', store=True)

    code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')
    ], 'Type of Operation', required=True, default='internal')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self.env['ir.rule'].clear_cache()
        return super(StockPickingType, self).search_read(domain, fields, offset, limit, order)

    @api.depends('name')
    def _compute_import_name(self):
        for picking_type in self:
            if self.env.context.get('special_shortened_wh_name'):
                if picking_type.warehouse_id:
                    name = picking_type.warehouse_id.name
                else:
                    name = _('Customer') + ' (' + picking_type.name + ')'
            elif picking_type.warehouse_id:
                name = picking_type.warehouse_id.name + ': ' + picking_type.name
            else:
                name = picking_type.name

            picking_type.import_name = name
