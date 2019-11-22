# -*- coding: utf-8 -*-

from odoo import fields, models, api


class InterfaceConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_partner = fields.Boolean('Enable partner', config_parameter='aop_interface.enable_partner')
    partner_url = fields.Char('Partner url', config_parameter='aop_interface.partner_url')

    enable_task = fields.Boolean('Enable task', config_parameter='aop_interface.enable_task')
    task_url = fields.Char('Task url', config_parameter='aop_interface.task_url')

    enable_stock = fields.Boolean('Enable stock', config_parameter='aop_interface.enable_stock')
    stock_url = fields.Char('Stock query url', config_parameter='aop_interface.stock_url')

    enable_cancel_task = fields.Boolean('Cancel enable task', config_parameter='aop_interface.enable_cancel_task')
    cancel_task_url = fields.Char('Cancel task url', config_parameter='aop_interface.cancel_task_url')