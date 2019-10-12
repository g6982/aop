# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BaseWarehouse(models.Model):
    _name = 'base.warehouse'
    _description = 'Base warehouse'
    _sql_constraints = [('unique_name', 'unique(name)', 'must unique!')]
    _parent_name = "parent_id"
    _parent_store = True

    name = fields.Char('Name')
    warehouse_ids = fields.Many2many('stock.warehouse')

    parent_id = fields.Many2one(
        'base.warehouse', 'Parent base warehouse', index=True, ondelete='cascade')
    child_ids = fields.One2many('base.warehouse', 'parent_id', 'Contains')
    parent_path = fields.Char(index=True)

    @api.multi
    @api.constrains('parent_id')
    def check_recursion(self):
        for base_id in self:
            if not super(BaseWarehouse, base_id)._check_recursion():
                raise UserError(
                    _('You can not create recursive base warehouse.'),
                )