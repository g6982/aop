# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CustomerAopContract(models.Model):
    _inherit = 'aop.contract'
    _name = 'customer.aop.contract'
    _description = 'customer aop contract'

    delivery_carrier_ids = fields.One2many('delivery.carrier', 'customer_contract_id', string="Contract terms")
    contract_rule_ids = fields.One2many('customer.contract.stock.rule.line', 'rule_contract_id', 'Contract rule line')

    # 通用的方法来查找数据
    def find_customer_delivery_carrier_id(self, contract_ids, sale_order_line_id):
        pass


class CustomerStockRuleLine(models.Model):
    _inherit = 'contract.stock.rule.line'
    _name = 'customer.contract.stock.rule.line'

    rule_contract_id = fields.Many2one('customer.aop.contract', 'Contract')
