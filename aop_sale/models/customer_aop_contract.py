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
    @api.multi
    def find_customer_delivery_carrier_id(self, contract_ids, from_location_id, to_location_id, order_line_id):
        latest_carrier_id = ''
        color_contract_line_ids = ''
        for contract_id in contract_ids:
            # 已经找到了，退出
            if latest_carrier_id:
                continue
            contract_line_ids = contract_id.mapped('delivery_carrier_ids')

            # 先 判断路由，来源地，目的地，再去判断产品
            contract_line_ids = contract_line_ids.filtered(
                lambda x:
                x.from_location_id.id == from_location_id.id and
                x.to_location_id.id == to_location_id.id and
                x.route_id.id == order_line_id.route_id.id
            )

            # 没有过滤出条款
            if not contract_line_ids:
                continue

            # 判断货物
            product_contract_line_ids = contract_line_ids.filtered(
                lambda x:
                x.product_id.id == order_line_id.product_id.id
            )

            # 如果找到了货物的，再去找颜色 (前提是订单行存在颜色)
            if product_contract_line_ids and order_line_id.product_color:
                color_contract_line_ids = product_contract_line_ids.filtered(
                    lambda x:
                    x.product_color == order_line_id.product_color
                )
            # 如果找到了颜色，就使用颜色过滤的
            if color_contract_line_ids:
                contract_line_ids = color_contract_line_ids

            # 如果没有找到对应颜色的
            if product_contract_line_ids and not color_contract_line_ids:
                contract_line_ids = product_contract_line_ids

            if not product_contract_line_ids:
                no_product_contract_line_ids = contract_line_ids.filtered(
                    lambda x:
                    not x.product_id
                )
                if no_product_contract_line_ids:
                    contract_line_ids = no_product_contract_line_ids
            _logger.info({
                'contract_line_ids': contract_line_ids,
                'from_location_id': from_location_id,
                'to': to_location_id,
                'product_id': order_line_id.product_id.display_name
            })
            # 使用第一条记录
            line_id = contract_line_ids[0]
            # 判断合同条款中是否存在"转到条款",如存在,获取"转到条款"
            carrier_id = line_id if not line_id.goto_delivery_carrier_id else line_id.goto_delivery_carrier_id
            latest_carrier_id = carrier_id

        return latest_carrier_id


class CustomerStockRuleLine(models.Model):
    _inherit = 'contract.stock.rule.line'
    _name = 'customer.contract.stock.rule.line'

    rule_contract_id = fields.Many2one('customer.aop.contract', 'Contract')
