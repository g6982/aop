# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class InvoiceNoTaxInvoice(models.Model):
    _name = 'invoice.no.tax.invoice'

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'the name must be unique!')
    ]

    name = fields.Char('Tax invoice no')
    partner_id = fields.Many2one('res.partner', 'Partner')
    invoice_line_ids = fields.Many2many('account.invoice.line')

    tax_invoice_line_ids = fields.One2many('account.tax.invoice.line', 'tax_invoice_id', string='Tax invoice line')

    opened_amount = fields.Float('Opened amount', compute='_compute_amount', store=True)
    actual_amount = fields.Float('Actual amount', compute='_compute_amount', store=True)
    balance_amount = fields.Float('Balance amount', compute='_compute_amount', store=True)

    @api.multi
    @api.depends('invoice_line_ids', 'tax_invoice_line_ids', 'tax_invoice_line_ids.tax_invoice_number')
    def _compute_amount(self):
        self.ensure_one()

        actual_amount = sum(line.price_unit for line in self.invoice_line_ids)
        opened_amount = sum(line.price_unit for line in self.tax_invoice_line_ids)

        actual_amount = self.update_number_digit(actual_amount)
        self.actual_amount = actual_amount
        opened_amount = self.update_number_digit(opened_amount)
        self.opened_amount = opened_amount
        balance_amount = actual_amount - opened_amount
        self.balance_amount = balance_amount

    def update_number_digit(self, num):
        return round(float(num * 1000), -1) / 1000

    @api.multi
    def unlink(self):
        # 删除的时候。需要先对税务发票进行删除处理
        for line in self:
            if not line.tax_invoice_line_ids:
                continue
            line.tax_invoice_line_ids.mapped('invoice_id').unlink()
        return super(InvoiceNoTaxInvoice, self).unlink()

    @api.multi
    def action_continue_invoice(self):
        self.ensure_one()

        if float_is_zero(self.balance_amount, precision_rounding=0.001):
            raise UserWarning('Already done! You should not continue to make tax invoice!')

        context_wizard = {
            'default_tax_invoice_no': self.name,
            'active_ids': self.invoice_line_ids.ids,
            'invoice_model_name': 'account.invoice.line'
        }
        return {
            'name': _('invoice no'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'account.tax.invoice.wizard',
            'type': 'ir.actions.act_window',
            'context': context_wizard,
            'target': 'new',
        }


class AccountTaxInvoiceLine(models.Model):
    _inherit = 'account.tax.invoice.line'

    tax_invoice_id = fields.Many2one('invoice.no.tax.invoice')
    tax_invoice_number = fields.Char('Tax invoice number')
