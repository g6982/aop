# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_compare, float_is_zero

import logging

_logger = logging.getLogger(__name__)


# 审核批次号
class BatchReconciliationNumber(models.Model):
    _name = 'batch.reconciliation.number'

    name = fields.Char('Name')

    reconciliation_file_ids = fields.Many2many('reconciliation.file', string='Reconciliation list')
    invoice_line_ids = fields.Many2many('account.invoice.line')

    verify_batch_id = fields.Many2one('verify.batch.reconciliation', string='Verify', index=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    # 对帐
    def confirm_account_invoice(self):
        for line in self:
            ids = list(set(line.invoice_line_ids.mapped('invoice_id').ids))
            account_invoice_ids = self.env['account.invoice'].browse(ids)
            account_invoice_ids.action_invoice_open()

            # 把对账数据的单车价格写入回款结算清单的确认价
            for reconciliation_id in line.reconciliation_file_ids:
                price_unit = reconciliation_id.price_unit
                reconciliation_account_invoice_ids = reconciliation_id.re_line_ids.mapped('invoice_line_id')
                ids = list(set(reconciliation_account_invoice_ids.ids))
                account_invoice_line_ids = self.env['account.invoice.line'].browse(ids).filtered(lambda x: x.price_unit > 0)
                account_invoice_line_ids.write({
                    'price_unit': price_unit
                })

            line.state = 'done'
