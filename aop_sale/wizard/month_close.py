# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import xlrd
from odoo.exceptions import UserError
import binascii
import traceback
import re

_logger = logging.getLogger(__name__)


class MonthClose(models.TransientModel):
    _name = 'month.close.wizard'

    period_id = fields.Many2one('account.period', string='Period')

    # 1. 将没有生成结算清单的销售订单行，生成结算清单
    # 2. 标记月结状态
    def start_generate_monthly(self):
        if self.period_id.monthly_state:
            raise UserError('Please cancel monthly first')

        sale_order_line_ids = self.find_sale_order_not_invoice()
        
        if sale_order_line_ids:
            context = {
                'active_ids': [x.mapped('order_id').id for x in sale_order_line_ids],
                'period_id': self.period_id.id
            }
            return {
                'name': _('Make invoice'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'sale.advance.payment.inv',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        self.period_id.monthly_state = True

    def cancel_monthly(self):
        self.period_id.monthly_state = False

    # 筛选当前期间内的数据
    def find_sale_order_not_invoice(self):
        res = self.env['sale.order.line'].search([
            ('invoice_lines', '=', False),
            ('write_date', '>=', self.period_id.date_start),
            ('write_date', '<=', self.period_id.date_stop),
            ('order_id.state', '!=', 'draft')
        ])
        if not res:
            return False
        line_ids = []
        for sale_line_id in res:
            if any(x.state != 'done' for x in sale_line_id.stock_picking_ids):
                continue
            line_ids.append(sale_line_id)

        return line_ids
