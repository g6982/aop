# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [('unique_name', 'unique(name)', 'the name must be unique!')]
