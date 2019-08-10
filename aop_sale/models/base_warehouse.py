# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BaseWarehouse(models.Model):
    _name = 'base.warehouse'
    _description = 'Base warehouse'
    _sql_constraints = [('unique_name', 'unique(name)', 'must unique!')]

    name = fields.Char('Name')
    warehouse_ids = fields.Many2many('stock.warehouse')
