# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    account_tax_invoice_id = fields.Many2one('account.tax.invoice', 'Account tax invoice')
    reconciliation_batch_no = fields.Char('Reconciliation batch no')

    account_batch_no = fields.Char(string='Account batch')

    account_period_id = fields.Many2one('account.period', string='Period', compute='_compute_period_id')

    tmp_estimate = fields.Float('Temporary estimate', compute='_compute_estimate_billing_receipt', store=True)
    pre_billing = fields.Float('Pre-billing', compute='_compute_estimate_billing_receipt', store=True)
    advance_receipt = fields.Float('Advance receipt', compute='_compute_estimate_billing_receipt', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('account', 'Account Checking'),
        ('open', 'Open'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    # 任务完成生成的有完成时间
    # 没有完成的(预收)就用当前时间
    @api.multi
    @api.depends('date_invoice')
    def _compute_period_id(self):
        period_obj = self.env['account.period']
        for line in self:
            if line.date_invoice:
                current_period_id = period_obj.search([
                    ('date_start', '<=', line.date_invoice),
                    ('date_stop', '>=', line.date_invoice)
                ])
                line.account_period_id = current_period_id.id


    @api.depends('invoice_line_ids.pre_billing', 'invoice_line_ids.tmp_estimate', 'invoice_line_ids.advance_receipt')
    def _compute_estimate_billing_receipt(self):
        for line in self:
            line.pre_billing = sum(x.pre_billing for x in line.invoice_line_ids)
            line.tmp_estimate = sum(x.tmp_estimate for x in line.invoice_line_ids)
            line.advance_receipt = sum(x.advance_receipt for x in line.invoice_line_ids)

    def create_account_tax_invoice(self):
        if self.account_tax_invoice_id:
            view = self.env.ref('aop_sale.tax_invoice_form')
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.tax.invoice',
                'views': [(view.id, 'form')],
                'res_id': self.account_tax_invoice_id.id,
                'target': 'current'
            }
        else:
            view_id = self.env.ref('aop_sale.view_account_tax_invoice_wizard')

            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.tax.invoice.wizard',
                'views': [(view_id.id, 'form')],
                'res_id': False,
                'target': 'new'
            }
        # tax_invoice = self.env['account.tax.invoice']
        # tax_account_id = self._create_account_tax_invoice(tax_invoice)
        # self.write({
        #     'account_tax_invoice_id': tax_account_id.id
        # })
        # _logger.info('create success {}'.format(tax_account_id))
        # return True

    def _create_account_tax_invoice(self, tax_invoice):
        data = self._parse_account_tax_data()
        tax_account_id = tax_invoice.create(data)
        return tax_account_id

    def _parse_account_tax_data(self):
        line_data = []
        for line_id in self.invoice_line_ids:
            line_data.append((0, 0, {
                'name': line_id.name,
                'origin': line_id.origin,
                'account_id': line_id.account_id.id,
                'price_unit': line_id.price_unit,
                'quantity': line_id.quantity,
                'discount': line_id.discount,
                'uom_id': line_id.uom_id.id,
                'product_id': line_id.product_id.id,
                'invoice_line_tax_ids': [(6, 0, line_id.invoice_line_tax_ids.ids)],
                'analytic_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
                # 'account_analytic_id': line_id.analytic_account_id.id if line_id.analytic_account_id else False,
            }))
        data = {
            'name': u'税务发票' + ' ' + self.name.split(' ')[-1] if self.name else '',
            'origin': self.name,
            'type': self.type,
            'reference': self.reference,
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_id.property_account_position_id.id,
            'user_id': self.user_id.id,
            'comment': self.comment,
        }
        data.update({
            'invoice_line_ids': line_data
        })
        return data

    def _prepare_invoice_line_from_po_line(self, line):
        res = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)

        if line.sale_line_id:
            res.update({
                'sale_order_line_id': line.sale_line_id
            })
        return res


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    tax_invoice_amount = fields.Float('Tax invoice amount')

    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale order line')
    line_price_subtotal = fields.Monetary(related='sale_order_line_id.price_subtotal', readonly=True)
    line_price_unit =  fields.Float(related='sale_order_line_id.price_unit', readonly=True)

    from_location_id = fields.Many2one('res.partner', related='sale_order_line_id.from_location_id', readonly=True)
    to_location_id = fields.Many2one('res.partner', related='sale_order_line_id.to_location_id', readonly=True)
    vin_id = fields.Many2one('stock.production.lot', 'VIN', related='sale_order_line_id.vin', readonly=True)
    contract_price = fields.Float('Contract price')
    purchase_line_price = fields.Monetary(related='purchase_line_id.price_subtotal')

    tmp_estimate = fields.Float('Temporary estimate')

    pre_billing = fields.Float('Pre-billing')
    advance_receipt = fields.Float('Advance receipt')

    # customer_price = fields.Float('Customer price')

