# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SupplierAopContract(models.Model):
    _inherit = 'aop.contract'
    _name = 'supplier.aop.contract'
    _description = 'supplier aop contract'

    delivery_carrier_ids = fields.One2many('delivery.carrier', 'supplier_contract_id', string="Contract terms")
    contract_rule_ids = fields.One2many('supplier.contract.stock.rule.line', 'rule_contract_id', 'Contract rule line')


class SupplierStockRuleLine(models.Model):
    _inherit = 'contract.stock.rule.line'
    _name = 'supplier.contract.stock.rule.line'

    rule_contract_id = fields.Many2one('supplier.aop.contract', 'Contract')
