# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class AccountTaxInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.tax.invoice'
    _description = 'account tax invoice'

    _sql_constrain = [('unique_tax_no', 'unique(tax_invoice_no, company_id)', 'Tax invoice no must be unique!')]

    invoice_line_ids = fields.One2many('account.tax.invoice.line', 'invoice_id', string='Invoice Lines',
                                       readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    tax_invoice_no = fields.Char('Tax invoice no')

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        pass


class AccountTaxInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _name = 'account.tax.invoice.line'

    invoice_id = fields.Many2one('account.tax.invoice', string='Invoice Reference',
                                 ondelete='cascade', index=True)
