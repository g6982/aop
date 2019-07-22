# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    product_id = fields.Many2one('product.product', string='Products', domain=[('type', '=', 'product')],
                                 required=False,
                                 ondelete='restrict')

    product_template_id = fields.Many2one('product.template', string='Products', domain=[('type', '=', 'product')],
                                          required=False,
                                          ondelete='restrict')
    contract_id = fields.Many2one('aop.contract', 'contract')

    route_id = fields.Many2one('stock.location.route', string='Route')

    service_product_id = fields.Many2one('product.product', string='Service product')
    start_position = fields.Many2one('res.partner', 'Outset')
    end_position = fields.Many2one('res.partner', 'End')

    rule_service_product_ids = fields.One2many('rule.service.product', 'carrier_id', 'Rule & product')

    fixed_price = fields.Float(compute='_compute_fixed_price', inverse='_set_product_fixed_price', store=True,
                               string='Fixed Price')

    @api.onchange('route_id')
    def fill_rule_service_product(self):
        data = []
        for rule_id in self.route_id.rule_ids:
            data.append((0, 0, {
                'route_id': self.route_id.id,
                'rule_id': rule_id.id,
                'service_product_id': False
            }))
        self.rule_service_product_ids = data

    @api.depends('service_product_id.list_price', 'service_product_id.product_tmpl_id.list_price')
    def _compute_fixed_price(self):
        for carrier in self:
            carrier.fixed_price = carrier.service_product_id.list_price

    def _set_product_fixed_price(self):
        pass
        # for carrier in self:
        #     _logger.info({
        #         'carrier': carrier
        #     })
        #     carrier.service_product_id.list_price = carrier.fixed_price


class RuleServiceProduct(models.Model):
    _name = 'rule.service.product'

    carrier_id = fields.Many2one('delivery.carrier')
    route_id = fields.Many2one('stock.location.route', string='Route')
    rule_id = fields.Many2one('stock.rule', string='Rule')
    service_product_id = fields.Many2one('product.product', string='Service product', domain="[('type','=','service')]")
    price_total = fields.Float('Price')
