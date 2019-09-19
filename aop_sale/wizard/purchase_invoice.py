# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
_logger = logging.getLogger(__name__)


class PurchaseOrderInvoiceWizard(models.TransientModel):
    _name = 'purchase.order.invoice.wizard'

    purchase_order_ids = fields.Many2many('purchase.order')
    reconciliation_batch_no = fields.Char('Reconciliation batch no', required=True)

    @api.model
    def default_get(self, fields_list):
        if self._context.get('active_model', False) == 'purchase.order':
            return []
        else:
            res = super(PurchaseOrderInvoiceWizard, self).default_get(fields_list)
            ids = self._context.get('active_ids', [])
            res['purchase_order_ids'] = [(6, 0, ids)]
            return res

    def judge_purchase_not_draft(self):
        for line_id in self.purchase_order_ids:
            if line_id.state in ('draft', 'sent', 'cancel'):
                raise UserError('The order can\'t be draft')

    def generate_account_invoice(self):
        self.judge_purchase_not_draft()

        purchase_ids = self.purchase_order_ids
        data = []
        reconciliation_batch_no = self.reconciliation_batch_no
        for line in purchase_ids:
            invoice_data = {
                'partner_id': line.partner_id.id,
                'partner_shipping_id': line.partner_id.id,
                'company_id': line.company_id.id if line.company_id else False,
                'type': 'in_invoice',
                'purchase_id': line.id,
                'origin': line.name,
                'currency_id': line.currency_id.id,
                'account_id': line.partner_id.property_account_receivable_id.id,
                'date_invoice': fields.Date.today(),
                'reconciliation_batch_no': reconciliation_batch_no
            }
            line_data = []
            for line_id in line.order_line:
                # 如果已经生成了。不需要继续生成
                if line_id.invoice_lines:
                    continue
                tmp = self._prepare_invoice_line_from_po_line(line_id)
                line_data.append((0, 0, tmp))

            if not line_data:
                continue
            invoice_data.update({
                'invoice_line_ids': line_data
            })
            data.append(invoice_data)
        invoice_obj = self.env['account.invoice']
        invoice_obj.create(data)

    def _prepare_invoice_line_from_po_line(self, line):
        if line.product_id.purchase_method == 'purchase':
            qty = line.product_qty - line.qty_invoiced
        else:
            qty = line.qty_received - line.qty_invoiced
        if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
            qty = 0.0
        taxes = line.taxes_id
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id,
                                                                        line.order_id.partner_id)
        invoice_line = self.env['account.invoice.line']
        # date = self.date or self.date_invoice
        date = False
        journal_domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', line.order_id.company_id.id),
            ('currency_id', '=', line.order_id.partner_id.property_purchase_currency_id.id),
        ]
        journal_id = self.env['account.journal'].search(journal_domain, limit=1)
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name + ': ' + line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context(
                {'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': line.order_id.currency_id._convert(
                line.price_unit, line.order_id.currency_id, line.company_id, date or fields.Date.today(), round=False),
            'quantity': qty,
            'discount': 0.0,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id,
                                                        self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

