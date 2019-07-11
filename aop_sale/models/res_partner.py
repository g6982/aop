# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 名字不重复的限制
    # 参考的限制
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'the name must be unique!'),
        ('unique_ref', 'unique(ref)', 'the ref must be unique!')
    ]
