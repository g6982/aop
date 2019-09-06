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

    account_period_id = fields.Many2one('account.period', string='Period')

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


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    tax_invoice_amount = fields.Float('Tax invoice amount')

    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale order line')
    from_location_id = fields.Many2one('res.partner', related='sale_order_line_id.from_location_id', readonly=True)
    to_location_id = fields.Many2one('res.partner', related='sale_order_line_id.to_location_id', readonly=True)

