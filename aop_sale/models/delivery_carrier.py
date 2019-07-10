# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    product_id = fields.Many2one('product.product', string='Products', domain=[('type', '=', 'product')],
                                 required=False,
                                 ondelete='restrict')

    product_template_id = fields.Many2one('product.template', string='Products', domain=[('type', '=', 'product')],
                                          required=False,
                                          ondelete='restrict')
    contract_id = fields.Many2one('aop.contract', 'contract')

    route_ids = fields.Many2many('stock.location.route', string='Routes')
    rule_ids = fields.Many2many('stock.rule', string='Rules')

    service_product_id = fields.Many2one('product.product', string='Service product')
    start_position = fields.Many2one('res.partner', 'Outset')
    end_position = fields.Many2one('res.partner', 'End')

