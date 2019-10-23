# -*- coding: utf-8 -*-

from odoo import fields, models


class InterafceConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_url = fields.Char('Partner url')

