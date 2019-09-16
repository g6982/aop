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
        sale_order_line_ids = self.find_sale_order_not_invoice()
        if sale_order_line_ids:
            context = {
                'active_ids': sale_order_line_ids.mapped('order_id').ids,
                'period_id': self.period_id
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
        pass

    def find_sale_order_not_invoice(self):
        res = self.env['sale.order.line'].search([
            ('invoice_lines', '=', False)
        ])
        return res
