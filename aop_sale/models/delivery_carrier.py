# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    product_id = fields.Many2one('product.product', string='Products', domain=[('type', '=', 'product')], required=False,
                                 ondelete='restrict')
    aop_route_id = fields.One2many('aop.route', 'aop_id', 'Aop Route ID')
    aop_route_ids = fields.Many2many('aop.route', string='AOP route')
    contract_id = fields.Many2one('aop.contract', 'contract')
    route_id = fields.Many2one('stock.location.route', 'Route')
    service_product_id = fields.Many2one('product.product', string='Service product')
    start_position = fields.Char('Outset')
    end_position = fields.Char('End')
