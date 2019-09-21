# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountTaxInvoiceWizard(models.TransientModel):
    _name = 'account.tax.invoice.wizard'
    _description = 'the way to make tax invoice'

    tax_invoice_no = fields.Char('Tax invoice no', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    invoice_line_ids = fields.Many2many('account.invoice.line', string='Invoice line')
    tax_invoice_method = fields.Selection([
        ('all', 'All'),
        ('part_amount', 'Part-amount'),
        ('part_percent', 'Part-rate'),
    ], required=True)
    tax_invoice_number = fields.Float('Tax invoice number')

    @api.model
    def _compute_tax_invoice_no(self):
        tax_invoice_obj = self.env['account.tax.invoice']
        tax_domain = [
            ('tax_invoice_no', '!=', False),
        ]
        tax_invoice_ids = tax_invoice_obj.search(tax_domain)

        data = []
        if not tax_invoice_ids:
            return []

        for x in list(set(tax_invoice_ids.mapped('tax_invoice_no'))):
            data.append(
                (x, x)
            )
        return data

    tax_invoices_no = fields.Selection(selection=lambda self: self._compute_tax_invoice_no(), string='Tax invoices no')

    @api.onchange('tax_invoices_no')
    def _onchange_tax_invoices_no(self):
        if self.tax_invoices_no:
            self.tax_invoice_no = self.tax_invoices_no
            invoice_lines = self.env['account.tax.invoice'].search([('tax_invoice_no', '=', self.tax_invoices_no)])
            self.invoice_line_ids = [(6, 0, invoice_lines.mapped('invoice_line_ids').mapped('invoice_line_id').ids if invoice_lines.mapped('invoice_line_ids') else [])]

    @api.model
    def default_get(self, fields_list):
        res = super(AccountTaxInvoiceWizard, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            invoice_ids = self.env['account.invoice'].browse(self.env.context.get('active_ids'))
            invoice_line_ids = invoice_ids.mapped('invoice_line_ids')
            partner_id = invoice_line_ids.mapped('partner_id')
            invoice_line_ids = invoice_line_ids.filtered(lambda x: x.tax_invoice_amount != x.price_subtotal)
            res.update({
                'invoice_line_ids': [(6, 0, invoice_line_ids.ids)],
                'partner_id': partner_id[0].id
            })
        return res

    # 解析数据
    def _parse_account_tax_invoice_data(self):
        data = {
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'user_id': self.env.user.id,
            'tax_invoice_no': self.tax_invoice_no
        }
        return data

    # 数据行的数据
    def _parse_account_tax_invoice_line_data(self, tax_invoice_method, tax_invoice_number, invoice_line_ids):
        line_data = []
        for line_id in invoice_line_ids:
            # 获取金额数据
            amount = getattr(self, '_compute_invoice_amount_{type_name}'.format(
                type_name=tax_invoice_method
            ))(line_id, tax_invoice_number, invoice_line_ids)
            line_data.append((0, 0, {
                'product_id': line_id.product_id.id,
                'name': line_id.product_id.name,
                'quantity': 1,
                'uom_id': line_id.product_id.uom_id.id,
                'price_unit': amount,
                'account_id': line_id.account_id.id,
                'invoice_line_id': line_id.id
            }))
        return line_data

    # 全部
    def _compute_invoice_amount_all(self, line_id, tax_invoice_number, invoice_line_ids):
        left_amount = line_id.price_subtotal - line_id.tax_invoice_amount
        line_id.write({
            'tax_invoice_amount': line_id.price_subtotal,
            'tax_invoice_state': tax_invoice_state
        })
        return round(float(left_amount) * 1000, -1) / 1000

    # 部分-金额
    def _compute_invoice_amount_part_amount(self, line_id, tax_invoice_number, invoice_line_ids):
        left_amount = line_id.price_subtotal - line_id.tax_invoice_amount
        if left_amount > tax_invoice_number / len(invoice_line_ids):
            line_id.write({
                'tax_invoice_amount': line_id.tax_invoice_amount + round(
                    float(tax_invoice_number / len(invoice_line_ids) * 1000), -1) / 1000
            })
            return round(float(tax_invoice_number / len(invoice_line_ids) * 1000), -1) / 1000
        else:
            line_id.write({
                'tax_invoice_amount': line_id.price_subtotal
            })
            return left_amount

    # 部分-比率
    def _compute_invoice_amount_part_percent(self, line_id, tax_invoice_number, invoice_line_ids):
        res = (line_id.price_subtotal - line_id.tax_invoice_amount) * (tax_invoice_number / 100)
        line_id.write({
            'tax_invoice_amount': line_id.tax_invoice_amount + round(float(res * 1000), -1) / 1000
        })
        return round(float(res * 1000), -1) / 1000

    def create_account_tax_invoice(self):
        data = self._parse_account_tax_invoice_data()
        line_data = self._parse_account_tax_invoice_line_data(self.tax_invoice_method, self.tax_invoice_number,
                                                              self.invoice_line_ids)

        data.update({
            'invoice_line_ids': line_data
        })
        tax_invoice_obj = self.env['account.tax.invoice']
        res = tax_invoice_obj.create(data)
