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
        pass


class ChangeToLocationByOrderLineDetail(models.TransientModel):
    _name = 'change.to.location.by.order.line.detail'

    change_id = fields.Many2one('change.to.location.by.order.line')
    from_location_id = fields.Many2one('stock.location', 'From')
    to_location_id = fields.Many2one('stock.location', 'To')
