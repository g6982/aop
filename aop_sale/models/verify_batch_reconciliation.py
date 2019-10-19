# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_compare, float_is_zero

import logging

_logger = logging.getLogger(__name__)


# 审核批次号
class VerifyBatchReconciliation(models.Model):
    _name = 'verify.batch.reconciliation'

    name = fields.Char('Name')

    invoice_line_ids = fields.Many2many('account.invoice.line')
    reconciliation_file_ids = fields.Many2many('reconciliation.file', string='Reconciliation list')
    batch_reconciliation_ids = fields.Many2many('batch.reconciliation.number', string='Reconciliation batch')
