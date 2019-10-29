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


class PurchaseBatchInvoiceLine(models.Model):
    _name = 'purchase.batch.invoice.line'

    purchase_batch_id = fields.Many2one('purchase.batch.invoice')

    invoice_line_id = fields.Many2one('account.invoice.line')
