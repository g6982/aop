# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class PurchaseInvoiceBatchNo(models.Model):
    _name = 'purchase.invoice.batch.no'

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'the name must be unique!')
    ]

    name = fields.Char('Reconciliation batch no')
    invoice_line_ids = fields.Many2many('account.invoice.line')
    partner_id = fields.Many2one('res.partner', string='Supplier')

    invoice_no = fields.Char('Invoice no')

    def action_confirm(self):
        pass
