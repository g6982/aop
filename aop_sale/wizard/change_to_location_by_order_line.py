# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import re
import datetime

_logger = logging.getLogger(__name__)


class ChangeToLocationByOrderLine(models.TransientModel):
    _name = 'change.to.location.by.order.line'

    order_line_ids = fields.Many2many('sale.order.line', string='Order lines')

    line_ids = fields.One2many('change.to.location.by.order.line.detail', 'change_id', 'Line ids')

    @api.model
    def default_get(self, fields_list):
        res = super(ChangeToLocationByOrderLine, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            res.update({
                'order_line_ids': [(6, 0, self.env.context.get('active_ids'))]
            })
        return res

    # 先判断，选择的起点和终点，是否都在路由上
    # 再调度
    def dispatch_location_id_2_new_location_id(self):
        if not self.line_ids:
            raise ValueError('You must select from/to location')
        start_location_id = self.line_ids[0].from_location_id
        end_location_id = self.line_ids[-1].to_location_id

        for sale_order_line_id in self.order_line_ids:
            from_location_ids = sale_order_line_id.route_id.rule_ids.mapped('location_src_id')
            to_location_ids = sale_order_line_id.route_id.rule_ids.mapped('location_id')

            # 验证位置在路由内
            if start_location_id.id not in from_location_ids.ids or end_location_id.id not in to_location_ids.ids:
                raise ValueError('Value Error')


class ChangeToLocationByOrderLineDetail(models.TransientModel):
    _name = 'change.to.location.by.order.line.detail'

    change_id = fields.Many2one('change.to.location.by.order.line')
    from_location_id = fields.Many2one('stock.location', 'From')
    to_location_id = fields.Many2one('stock.location', 'To')
