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

    fixed_price = fields.Float(compute='_compute_fixed_price', inverse=False, store=True,
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

    @api.depends('rule_service_product_ids.price_total', 'rule_service_product_ids',
                 'rule_service_product_ids.price_unit', 'rule_service_product_ids.kilo_meter')
    def _compute_fixed_price(self):
        for carrier in self:
            carrier.fixed_price = sum(line.price_total for line in carrier.rule_service_product_ids)

    def _set_product_fixed_price(self):
        pass
        # for carrier in self:
        #     carrier.fixed_price = sum(line.price_total for line in carrier.rule_service_product_ids)


class RuleServiceProduct(models.Model):
    _name = 'rule.service.product'

    carrier_id = fields.Many2one('delivery.carrier')
    route_id = fields.Many2one('stock.location.route', string='Route')
    rule_id = fields.Many2one('stock.rule', string='Rule')
    service_product_id = fields.Many2one('product.product', string='Service product', domain="[('type','=','service')]")
    price_total = fields.Float('Price', compute='_compute_price_total', inverse='_set_fixed_price', store=True)

    kilo_meter = fields.Float('Kilometer')
    price_unit = fields.Float('Price Unit')

    child_location_lines = fields.One2many('rule.child.location.price', 'rule_partner_product_price',
                                           string='Child price')

    delivery_type = fields.Selection([('fixed', 'Fixed'), ('base_on_rule', 'Base on rule')], default='fixed')
    price_rule_ids = fields.One2many('delivery.price.rule', 'rule_service_product_id')

    @api.depends('kilo_meter', 'price_unit')
    def _compute_price_total(self):
        for line in self:
            line.price_total = line.price_unit * line.kilo_meter

    def _set_fixed_price(self):
        pass


class ChildLocationPrice(models.Model):
    _name = 'rule.child.location.price'
    _description = 'child location price'

    location_id = fields.Many2one('stock.location', 'Location')
    kilo_meter = fields.Float('Kilometer')
    price_unit = fields.Float('Price Unit')
    price_total = fields.Float('Price', compute='_compute_price_total', inverse='_set_fixed_price', store=True)

    rule_partner_product_price = fields.Many2one('rule.service.product')

    delivery_type = fields.Selection([('fixed', 'Fixed'), ('base_on_rule', 'Base on rule')], default='fixed')
    price_rule_ids = fields.One2many('delivery.price.rule', 'rule_child_location_id')

    @api.depends('kilo_meter', 'price_unit')
    def _compute_price_total(self):
        for line in self:
            line.price_total = line.price_unit * line.kilo_meter

    def _set_fixed_price(self):
        pass


class DeliveryPriceRule(models.Model):
    _inherit = "delivery.price.rule"

    rule_service_product_id = fields.Many2one('rule.service.product', 'Service product line', required=True,
                                              ondelete='cascade')
    rule_child_location_id = fields.Many2one('rule.child.partner.price', 'Child price', required=True,
                                             ondelete='cascade')

    variable = fields.Selection([
        ('kilometer', 'Kilometer'),
        ('weight', 'Weight'),
        ('volume', 'Volume'),
        ('wv', 'Weight * Volume'),
        ('price', 'Price'),
        ('quantity', 'Quantity')
    ], required=True, default='kilometer')

    variable_factor = fields.Selection(
        [('kilometer', 'Kilometer'), ('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'),
         ('price', 'Price'),
         ('quantity', 'Quantity')], 'Variable Factor', required=True, default='kilometer')
