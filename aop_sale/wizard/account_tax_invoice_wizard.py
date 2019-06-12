# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountTaxInvoiceWizard(models.TransientModel):
    _name = 'account.tax.invoice.wizard'
    _description = 'the way to make tax invoice'

    tax_invoice_no = fields.Char('Tax invoice no')
    invoice_line_ids = fields.Many2many('account.invoice.line', string='Invoice line')
    tax_invoice_method = fields.Selection([
        ('all', 'All'),
        ('part_amount', 'Part-amount'),
        ('part_percent', 'Part-rate'),
    ])
    tax_invoice_number = fields.Float('Tax invoice number')

    @api.model
    def default_get(self, fields_list):
        res = super(AccountTaxInvoiceWizard, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            invoice_ids = self.env['account.invoice'].browse(self.env.context.get('active_ids'))
            invoice_line_ids = invoice_ids.mapped('invoice_line_ids')
            invoice_line_ids = invoice_line_ids.filtered(lambda x: x.tax_invoice_amount != x.price_subtotal)
            res.update({
                'invoice_line_ids': [(6, 0, invoice_line_ids.ids)]
            })
        return res

    def create_account_tax_invoice(self):
        pass

