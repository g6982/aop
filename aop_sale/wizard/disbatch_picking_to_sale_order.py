#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from itertools import groupby
import logging

_logger = logging.getLogger(__name__)


class DispatchPickingToSaleOrder(models.TransientModel):
    _name = 'dispatch.picking.to.sale.order'

    picking_ids = fields.Many2many('stock.picking', string='Picking')
    partner_id = fields.Many2one('res.partner', string='Customer')
    company_id = fields.Many2one('res.company', 'Company')

    @api.model
    def default_get(self, fields_list):
        res = super(DispatchPickingToSaleOrder, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            res.update({
                'picking_ids': [(6, 0, self.env.context.get('active_ids'))]
            })

        return res

    def parse_order_data(self):
        return {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id
        }

    def judge_picking_correct(self):
        if len(self.picking_ids) == 1:
            return True

        picking_ids = self.picking_ids.sorted(lambda x: x.id)

    # 订单数据
    def parse_from_to_location(self):
        picking_ids = self.picking_ids.sorted(lambda x: x.id)

        from_location_id = picking_ids[0].location_id
        to_location_id = picking_ids[-1].location_dest_id

        from_location_id = self.env['res.partner'].search([
            ('property_stock_customer', '=', from_location_id.id)
        ], limit=1)
        to_location_id = self.env['res.partner'].search([
            ('property_stock_customer', '=', to_location_id.id)
        ], limit=1)
        return from_location_id, to_location_id

    # 订单行
    def parse_order_line_data(self):
        line_data = []
        from_location_id, to_location_id = self.parse_from_to_location()
        for picking_id in self.picking_ids:
            tmp = {
                'product_id': picking_id.move_lines[0].product_id.id,
                'product_uom': picking_id.move_lines[0].product_id.uom_id.id,
                'from_location_id': from_location_id.id if from_location_id else False,
                'to_location_id': to_location_id.id if to_location_id else False
            }
            line_data.append(
                (0, 0, tmp)
            )
        return line_data

    # 创建销售订单
    def create_order(self):
        order_data = self.parse_order_data()
        line_data = self.parse_order_line_data()

        order_data.update({
            'order_line': line_data
        })

        res = self.env['sale.order'].sudo().create(order_data)

        view_id = self.env.ref('sale.view_quotation_tree_with_onboarding').id
        form_id = self.env.ref('sale.view_order_form').id

        # 跳转到导入成功后的tree界面
        return {
            'name': 'Order',
            'view_type': 'form',
            'view_id': False,
            'views': [(view_id, 'tree'), (form_id, 'form')],
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res.ids)],
            'limit': 80,
            'target': 'current',
        }
