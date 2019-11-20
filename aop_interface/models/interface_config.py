# -*- coding: utf-8 -*-

from odoo import fields, models, api


class InterfaceConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_url = fields.Char('Partner url', config_parameter='aop_interface.partner_url')
    task_url = fields.Char('Task url', config_parameter='aop_interface.task_url')

    @api.model
    def get_values(self):
        res = super(InterfaceConfig, self).get_values()
        return res

    @api.multi
    def set_values(self):
        res = super(InterfaceConfig, self).set_values()
        return res
