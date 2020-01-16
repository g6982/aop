# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"
    _parent_name = "parent_id"
    _parent_store = True
    _order = 'name'

    # 仓库名称不重复的限制
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'the name must be unique!')
    ]

    parent_id = fields.Many2one(
        'stock.warehouse', 'Parent warehouse', index=True, ondelete='cascade')
    child_ids = fields.One2many('stock.warehouse', 'parent_id', 'Contains')
    parent_path = fields.Char(index=True)

    code = fields.Char('Short Name', required=True, size=20, help="Short name used to identify your warehouse")

    company_id = fields.Many2one(readonly=False, required=False)
    type_id = fields.Many2one('stock.warehouse.type', 'Type')

    def _get_locations_values(self, vals):
        res = super(Warehouse, self)._get_locations_values(vals)
        res.get('lot_stock_id').update({
            'name': vals.get('name') if vals.get('name', False) else _('Stock')
        })
        return res

    @api.model
    def create(self, vals):
        if vals.get('company_id'):
            vals['company_id'] = False

        res = super(Warehouse, self).create(vals)

        return res

