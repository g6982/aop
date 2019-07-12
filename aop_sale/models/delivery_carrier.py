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

    route_ids = fields.Many2many('stock.location.route', string='Routes')
    rule_ids = fields.Many2many('stock.rule', string='Rules')

    service_product_id = fields.Many2one('product.product', string='Service product')
    start_position = fields.Many2one('res.partner', 'Outset')
    end_position = fields.Many2one('res.partner', 'End')

    rule_service_product_ids = fields.One2many('rule.service.product', 'carrier_id', 'Rule & product')

    @api.onchange('route_ids', 'rule_ids')
    def fill_rule_service_product(self):
        if self.route_ids and self.rule_ids:
            raise UserError('You can only choose route or rule')

        data = []
        for route_id in self.route_ids if self.route_ids else []:
            for rule_id in route_id.rule_ids:
                data.append((0, 0, {
                    'route_id': route_id.id,
                    'rule_id': rule_id.id,
                    'service_product_id': False
                }))
        for rule_line_id in self.rule_ids if self.rule_ids else []:
            _logger.info({
                '???' * 100: '100'
            })
            data.append((0, 0, {
                'rule_id': rule_line_id.id
            }))
        _logger.info({
            'data': data
        })
        # self.write({
        #     'rule_service_product_ids': data
        # })
        self.rule_service_product_ids = data


class RuleServiceProduct(models.Model):
    _name = 'rule.service.product'

    carrier_id = fields.Many2one('delivery.carrier')
    route_id = fields.Many2one('stock.location.route', string='Route')
    rule_id = fields.Many2one('stock.rule', string='Rule')
    service_product_id = fields.Many2one('product.product', string='Service product', domain="[('type','=','service')]")
