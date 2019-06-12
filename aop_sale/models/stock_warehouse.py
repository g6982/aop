# -*- coding: utf-8 -*-
from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"
    _parent_name = "parent_id"
    _parent_store = True
    _order = 'name'

    parent_id = fields.Many2one(
        'stock.warehouse', 'Parent warehouse', index=True, ondelete='cascade')
    child_ids = fields.One2many('stock.warehouse', 'parent_id', 'Contains')
    parent_path = fields.Char(index=True)
