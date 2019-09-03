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