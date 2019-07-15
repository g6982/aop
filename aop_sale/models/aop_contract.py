# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AopContract(models.Model):
    _name = 'aop.contract'
    _description = 'AOP contract'

    name = fields.Char('name', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    serial_number = fields.Char(string='Contract number')
    version_id = fields.Many2one('contract.version', string="Version")
    serial_no = fields.Char(string='Contract no')
    is_formal = fields.Boolean(string='Contract', default=True)
    project_id = fields.Many2one('contract.project', string="Project")
    date_start = fields.Date('Start date', required=True, default=fields.Date.today)
    date_end = fields.Date('End date')
    effective_date = fields.Date('Active date')
    expiry_date = fields.Date('Expire_date')
    source = fields.Char(string='Source')
    type = fields.Selection(
        [
            ('buyer', 'Buyer'),
            ('supplier', 'Supplier')
        ],
        string='Contract type',
        default='buyer')
    delivery_carrier_ids = fields.One2many('delivery.carrier', 'contract_id', string="Contract terms")
    aging = fields.Float('Aging(day)', default=1)
    contract_rule_ids = fields.One2many('contract.stock.rule.line', 'rule_contract_id', 'Contract rule line')

    @api.onchange('delivery_carrier_ids')
    def onchange_rule_line(self):
        data = []
        for delivery_id in self.delivery_carrier_ids:
            # for route_id in delivery_id.route_ids:
            for rule_id in delivery_id.route_id.rule_ids:
                data.append((0, 0, {
                    'route_id': delivery_id.route_id.id,
                    'rule_id': rule_id.id,
                    'service_product_id': False
                }))
        # _logger.info({
        #     'data': data
        # })
        self.contract_rule_ids = data


class ContractVersion(models.Model):
    _name = 'contract.version'

    name = fields.Char(string='Version')


class ContractProject(models.Model):
    _name = 'contract.project'

    name = fields.Char(string='Project')


class ContractStockRule(models.Model):
    _name = 'contract.stock.rule.line'

    name = fields.Char('Name', readonly=True, related='rule_id.name')
    route_id = fields.Many2one('stock.location.route', 'Route')
    rule_id = fields.Many2one('stock.rule', 'Rule')
    service_product_id = fields.Many2one('product.product', string='Product', domain=[('type', '=', 'service')])
    rule_contract_id = fields.Many2one('aop.contract', 'Contract')
    # fee = fields.Boolean('Fee?', compute='is_fee_rule', store=True)
    #
    # @api.multi
    # @api.depends('service_product_id')
    # def is_fee_rule(self):
    #     for line_id in self:
    #         if line_id.service_product_id:
    #             line_id.fee = True
    #         else:
    #             line_id.fee = False
