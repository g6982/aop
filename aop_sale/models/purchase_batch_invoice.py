# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_compare, float_is_zero

import logging

_logger = logging.getLogger(__name__)


class PurchaseBatchInvoice(models.Model):
    _name = 'purchase.batch.invoice'

    name = fields.Char('Name')
    tax_no = fields.Char('Tax no')
    batch_line_ids = fields.One2many('purchase.batch.invoice.line', 'purchase_batch_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    # 确认
    def confirm_account_invoice(self):
        for line in self:
            ids = list(set(line.batch_line_ids.mapped('invoice_line_id').mapped('invoice_id').ids))
            self.env['account.invoice'].browse(ids).action_invoice_open()
            line.state = 'done'


class PurchaseBatchInvoiceLine(models.Model):
    _name = 'purchase.batch.invoice.line'

    purchase_batch_id = fields.Many2one('purchase.batch.invoice')

    invoice_line_id = fields.Many2one('account.invoice.line')
