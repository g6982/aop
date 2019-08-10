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

    service_product_id = fields.Many2one(
        'product.product',
        string='Service products',
        domain="[('type', 'in', ['service'])]"
    )

    # @api.onchange('partner_id')
    # def onchange_domain_rule_ids(self):
    #     for line in self:
    #         if line.partner_id:
    #             allow_warehouse_ids = line.partner_id.allow_warehouse_ids.ids
    #             rules = self.find_all_rule_by_location(allow_warehouse_ids)
    #             line.rule_ids = [(6, 0, rules.ids)]
    #         else:
    #             line.rule_ids = False

    # # 通过位置查找规则
    # def find_all_rule_by_location(self, allow_warehouse_ids):
    #     '''
    #     :param allow_warehouse_ids: 允许的仓库
    #     :return: 允许的规则
    #     '''
    #     warehouse_ids = self.env['stock.warehouse'].browse(allow_warehouse_ids)
    #     location_ids = warehouse_ids.mapped('lot_stock_id')
    #     res = []
    #     for location_id in location_ids:
    #         self.find_all_location(location_id, res)
    #     rules = self.env['stock.rule'].search([
    #         '|',
    #         ('location_src_id', 'in', res),
    #         ('location_id', 'in', res)
    #     ])
    #     return rules

    # # 递归查找
    # def find_all_location(self, parent_location_id, res):
    #     '''
    #     :param parent_location_id: 位置
    #     :param res: 保存位置的 []
    #     :return: 所有位置的 []
    #     '''
    #     res.append(parent_location_id.id)
    #     if not parent_location_id.child_ids:
    #         return res
    #     for child_id in parent_location_id.child_ids:
    #         self.find_all_location(child_id, res)


class SupplierStockRuleLine(models.Model):
    _inherit = 'contract.stock.rule.line'
    _name = 'supplier.contract.stock.rule.line'

    rule_contract_id = fields.Many2one('supplier.aop.contract', 'Contract')
