# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_base_warehouse_ids = fields.Many2many('base.warehouse', string='Base')
