# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

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

    allow_customer_contract_ids = fields.Many2many('customer.aop.contract', string='Allow customer contract')
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

    def find_supplier_delivery_carrier_id(self, contract_ids, purchase_line_id):
        latest_carrier_id = ''
        for contract_id in contract_ids:
            if latest_carrier_id:
                continue
            picking_id = purchase_line_id.batch_stock_picking_id
            if not picking_id:
                return False
            # 获取需要过滤的产品
            move_lines = picking_id.move_lines
            move_line_ids = picking_id.move_line_ids

            # 接车没有明细行
            if not move_lines and picking_id.picking_incoming_number > 0:
                product_id = False
            else:
                product_id = move_lines[0].product_id

            from_location_id = picking_id.location_id
            to_location_id = picking_id.location_dest_id

            res = self.env['delivery.carrier'].search([
                ('from_location_id', '=', from_location_id.id),
                ('to_location_id', '=', to_location_id.id),
                ('supplier_contract_id', '=', contract_id.id),
                ('service_product_id', '=', purchase_line_id.product_id.id)
            ])
            if not res:
                from_location_id = move_line_ids[0].location_id
                to_location_id = move_line_ids[0].location_dest_id
                res = self.env['delivery.carrier'].search([
                    ('from_location_id', '=', from_location_id.id),
                    ('to_location_id', '=', to_location_id.id),
                    ('supplier_contract_id', '=', contract_id.id),
                    ('service_product_id', '=', purchase_line_id.product_id.id)
                ])

            if not res:
                continue

            # 如果存在货物，就应该去过滤货物
            product_res_ids = res.filtered(lambda x: x.product_id.id == product_id.id) if product_id else False
            if product_res_ids:
                res = product_res_ids
            if not product_res_ids:
                # 过滤出不包含货物的数据
                no_product_res = res.filtered(lambda x: not x.product_id)
                if no_product_res:
                    res = no_product_res
            # FIXME: 会出现多条么？
            latest_carrier_id = res[0] if res else False

        if not latest_carrier_id:
            raise UserError('Can not find correct supplier contract !')
        return latest_carrier_id


class SupplierStockRuleLine(models.Model):
    _inherit = 'contract.stock.rule.line'
    _name = 'supplier.contract.stock.rule.line'

    rule_contract_id = fields.Many2one('supplier.aop.contract', 'Contract')
