# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 名字不重复的限制
    # 参考的限制
    _sql_constraints = [
        ('unique_name_parent_id', 'unique(name, parent_id)', 'the name and parent_id must be unique!'),
        ('unique_ref', 'unique(ref)', 'the ref must be unique!')
    ]
