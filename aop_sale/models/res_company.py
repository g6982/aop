# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'the code must be unique')
    ]

    code = fields.Char('Code')
