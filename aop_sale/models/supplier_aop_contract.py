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

    rule_ids = fields.Many2many('stock.rule', string='Rules')

    @api.onchange('partner_id')
    def onchange_domain_rule_ids(self):
        for line in self:
            if line.partner_id:
                allow_warehouse_ids = line.partner_id.allow_warehouse_ids.ids
                rules = self.env['stock.rule'].search([('warehouse_id', 'in', allow_warehouse_ids)])
                line.rule_ids = [(6, 0, rules.ids)]


class SupplierStockRuleLine(models.Model):
    _inherit = 'contract.stock.rule.line'
    _name = 'supplier.contract.stock.rule.line'

    rule_contract_id = fields.Many2one('supplier.aop.contract', 'Contract')
