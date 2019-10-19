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

    def verify_account_invoice(self):
        for line in self:
            ids = list(set(line.invoice_line_ids.mapped('invoice_id').ids))
            self.env['account.invoice'].browse(ids).verify_reconciliation()
            line.state = 'done'
