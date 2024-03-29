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

    def judge_picking_correct(self, picking_ids):
        if len(picking_ids) == 1:
            return True

        picking_ids = picking_ids.sorted(lambda x: x.id).ids

        if not sorted(picking_ids) == list(range(min(picking_ids), max(picking_ids) + 1)):
            raise ValueError('Error!')

        # 订单数据
    def parse_from_to_location(self, picking_ids):
        picking_ids = picking_ids.sorted(lambda x: x.id)

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

        sale_order_line_ids = []
        for sale_order_line_id, lines in groupby(self.picking_ids, lambda x: x.sale_order_line_id):
            sale_order_line_ids.append(sale_order_line_id)

        sale_order_line_ids = list(set(sale_order_line_ids))
        for sale_order_line_id in sale_order_line_ids:
            picking_ids = self.picking_ids.filtered(lambda x: x.sale_order_line_id.id == sale_order_line_id.id)
            self.judge_picking_correct(picking_ids)

            from_location_id, to_location_id = self.parse_from_to_location(picking_ids)
            product_id = self.picking_ids[0].move_lines[0].product_id
            tmp = {
                'product_id': product_id.id,
                'product_uom': product_id.uom_id.id,
                'from_location_id': from_location_id.id if from_location_id else False,
                'to_location_id': to_location_id.id if to_location_id else False,
                'vin_code': sale_order_line_id.vin_code,
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
