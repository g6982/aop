# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


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
            if picking_type.warehouse_id:
                picking_type.import_name = picking_type.warehouse_id.name + ': ' + picking_type.name
            else:
                picking_type.import_name = picking_type.name

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        allow_warehouse_ids = self.env['stock.warehouse'].search([
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.user.company_id.id)
        ])
        args = args or [('warehouse_id', 'in', allow_warehouse_ids.ids)]
        domain = []
        if name:
            domain = ['|',
                      ('name', operator, name),
                      ('import_name', operator, name),
                      ]

        picking_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return self.browse(picking_ids).name_get()
