# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.osv import expression
import logging

class StockLocation(models.Model):
    _inherit = "stock.location"

    # 完整位置名称不重复的限制
    _sql_constraints = [
        ('unique_complete_name', 'unique(complete_name)', 'the name must be unique!')
    ]

    company_id = fields.Many2one(
        'res.company', 'Company',
        default=False, index=True,
        help='Leave this field empty if this route is shared between all companies')