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

    customer_contract_id = fields.Many2one('customer.aop.contract', 'Customer contract')
    supplier_contract_id = fields.Many2one('supplier.aop.contract', 'Supplier contract')

    route_id = fields.Many2one('stock.location.route', string='Route')

    service_product_id = fields.Many2one(
        'product.product',
        string='Service product',
        domain="[('type', 'in', ['service'])]"
    )
    start_position = fields.Many2one('res.partner', 'Outset')
    end_position = fields.Many2one('res.partner', 'End')

    rule_service_product_ids = fields.One2many('rule.service.product', 'carrier_id', 'Rule & product')

    fixed_price = fields.Float(compute='_compute_fixed_price', inverse='_set_product_fixed_price', store=True,
                               string='Fixed Price')
    product_standard_price = fields.Float('Standard price')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking type')

    from_location_id = fields.Many2one('stock.location', 'From location')
    to_location_id = fields.Many2one('stock.location', 'To location')

    # from_location_ids = fields.Many2many('stock.location', string='From locations', relation='delivery_carrier_from_location_ids')
    # to_location_ids = fields.Many2many('stock.location', string='To locations', relation='delivery_carrier_to_location_ids')

    rule_id = fields.Many2one('stock.rule', string='Rule')

    product_fixed_price = fields.Float('Product fixed price')

    @api.onchange('from_location_id', 'to_location_id')
    def domain_route_ids(self):
        if self.from_location_id and self.to_location_id:
            rule_obj = self.env['stock.location.route'].search([])
            rule_ids = []

            for rule_id in rule_obj:
                if not rule_id.rule_ids:
                    continue

                if rule_id.rule_ids[0].location_src_id.id == self.from_location_id.id and \
                        rule_id.rule_ids[-1].location_id.id == self.to_location_id.id:
                    rule_ids.append(rule_id.id)
            return {
                'domain': {
                    'route_id': [('id', 'in', rule_ids)]
                }
            }

    @api.onchange('route_id')
    def fill_rule_service_product(self):
        self.rule_service_product_ids = False
        data = []
        for rule_id in self.route_id.rule_ids:
            data.append((0, 0, {
                'route_id': self.route_id.id,
                'rule_id': rule_id.id,
            }))
        self.rule_service_product_ids = data

    # @api.onchange('picking_type_id')
    # def fill_default_location_id(self):
    #     for line in self:
    #         if line.picking_type_id:
    #             line.from_location_id = line.picking_type_id.default_location_src_id.id if line.picking_type_id.default_location_src_id else False
    #             line.to_location_id = line.picking_type_id.default_location_dest_id.id if line.picking_type_id.default_location_dest_id else False

    @api.onchange('service_product_id')
    def fill_service_product_price(self):
        for line in self:
            if line.service_product_id:
                line.product_standard_price = line.service_product_id.standard_price

    @api.depends('rule_service_product_ids.price_unit', 'rule_service_product_ids.kilo_meter')
    def _compute_fixed_price(self):
        for carrier in self:

            sum_fixed_price = sum(line.price_total for line in carrier.rule_service_product_ids)
            if sum_fixed_price > 0:
                _logger.info({
                    'carrier': carrier.product_fixed_price
                })
                carrier.fixed_price = sum_fixed_price
            else:
                carrier.fixed_price = carrier.product_fixed_price

    def _set_product_fixed_price(self):
        for carrier in self:
            carrier.product_fixed_price = carrier.fixed_price

    @api.model
    def create(self, vals):

        res = super(DeliveryCarrier, self).create(vals)

        # FIXME: 补丁。。。
        tmp = []
        for index_i, x in enumerate(res.rule_service_product_ids):
            tmp.append((1, x.id, {
                'route_id': res.route_id.id,
                'rule_id': res.route_id.rule_ids[index_i].id
            }))

        if not tmp:
            for rule_id in res.route_id.rule_ids:
                tmp.append((0, 0, {
                    'route_id': res.route_id.id,
                    'rule_id': rule_id.id,
                }))
        if tmp:
            res.write({
                'rule_service_product_ids': tmp
            })

        return res


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

    delivery_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('base_on_rule', 'Base on rule')
    ], default='fixed')
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

    partner_id = fields.Many2one('res.partner', 'Partner')
    kilo_meter = fields.Float('Kilometer', related='partner_id.kilometer_number', readonly=True)
    price_unit = fields.Float('Price Unit')
    price_total = fields.Float('Price', compute='_compute_price_total', inverse='_set_fixed_price', store=True)

    rule_partner_product_price = fields.Many2one('rule.service.product')

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
    # rule_child_location_id = fields.Many2one('rule.child.partner.price', 'Child price', required=True,
    #                                          ondelete='cascade')

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
