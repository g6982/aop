# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import time
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class MonthClose(models.TransientModel):
    _name = 'month.close.wizard'

    period_id = fields.Many2one('account.period', string='Period')

    # 1. 将没有生成结算清单的销售订单行，生成结算清单
    # 2. 标记月结状态
    def start_generate_monthly(self):
        if self.period_id.monthly_state:
            raise UserError('Please cancel monthly first')

        sale_order_line_ids = self.find_sale_order_not_invoice()

        if sale_order_line_ids:
            context = {
                'active_ids': [x.mapped('order_id').id for x in sale_order_line_ids],
                'period_id': self.period_id.id
            }
            return {
                'name': _('Make invoice'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'sale.advance.payment.inv',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        self._purchase_create_invoice()
        self.period_id.monthly_state = True

    def cancel_monthly(self):
        self.period_id.monthly_state = False

    # 筛选当前期间内的数据
    def find_sale_order_not_invoice(self):
        res = self.env['sale.order.line'].search([
            ('invoice_lines', '=', False),
            ('write_date', '>=', self.period_id.date_start),
            ('write_date', '<=', self.period_id.date_stop),
            ('order_id.state', '!=', 'draft')
        ])
        if not res:
            return False
        line_ids = []
        for sale_line_id in res:
            if any(x.state != 'done' for x in sale_line_id.stock_picking_ids):
                continue
            line_ids.append(sale_line_id)

        return line_ids

    # 采购单生成成本结算清单
    def _purchase_create_invoice(self):
        data = []
        purchase_ids = self.env['purchase.order'].search([('invoice_ids', '=', False)])
        reconciliation_batch_no = str(time.time())
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
                tmp = self._prepare_invoice_line_from_po_line(line_id)
                line_data.append((0, 0, tmp))
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
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
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
            'account_id': invoice_line.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': line.order_id.currency_id._convert(
                line.price_unit, line.order_id.currency_id, line.company_id, date or fields.Date.today(), round=False),
            'quantity': qty,
            'discount': 0.0,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id, self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data
