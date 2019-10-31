# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.addons.account.models.account_invoice import AccountInvoice
import logging
import math

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

    # _sql_constrain = [('unique_tax_no', 'unique(tax_invoice_no, company_id)', 'Tax invoice no must be unique!')]

    invoice_line_ids = fields.One2many('account.tax.invoice.line', 'invoice_id', string='Invoice Lines',
                                       readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    tax_invoice_no = fields.Char('Tax invoice no')

    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase', copy=False)

    period_month = fields.Char('Period', compute='_compute_contract_period', store=True)

    tax_invoice_number = fields.Char('Tax invoice number')

    # 根据合同的账期计算期间
    @api.multi
    @api.depends('create_date')
    def _compute_contract_period(self):
        for line_id in self:
            if line_id.period_month:
                continue

            # 找到合同的月份
            contract_period_month = self.get_contract_period_month(line_id)

            current_period_value = str(line_id.create_date.year) + '-' + str(line_id.create_date.month).zfill(2)

            period_code = self.next_year_month(current_period_value, contract_period_month)

            line_id.period_month = period_code

    # 客户合同 / 供应商合同， 账期
    def get_contract_period_month(self, invoice_id):
        search_domain = [('partner_id', '=', invoice_id.partner_id.id)]
        if invoice_id.type == 'out_invoice':
            res = self.env['customer.aop.contract'].search(search_domain)
        elif invoice_id.type == 'in_invoice':
            res = self.env['supplier.aop.contract'].search(search_domain)
        return res[0].period_month if res else 0

    # 获取下一个值
    def next_year_month(self, month_period, diff_number):
        diff_number_year = math.floor(diff_number / 12)
        diff_number_month = diff_number % 12
        month_period_month = int(month_period.split('-')[-1])
        month_period_year = int(month_period.split('-')[0])
        # 超出12个月的加，直接加年
        if diff_number_year >= 1:
            month_period_year += diff_number_year
        if month_period_month + diff_number_month > 12:
            month_period_year += 1
            month_period_month = (month_period_month + diff_number_month) % 12
        else:
            month_period_month += diff_number_month
        return str(month_period_year) + '-' + str(month_period_month).zfill(2)

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        pass

    @api.model
    def create(self, vals):
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, values):
        return super(AccountInvoice, self).write(values)

    @api.multi
    def unlink(self):
        # 删除之前，回滚数据
        # tax_invoice_line_ids
        for line in self:
            for line_id in line.invoice_line_ids:
                line_id.invoice_line_id.tax_invoice_amount -= line_id.price_unit
        return super(AccountInvoice, self).unlink()

    @api.multi
    def name_get(self):
        TAX_NAME = _('Tax invoices')
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.number or TAX_NAME, inv.name or '')))
        return result

class AccountTaxInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _name = 'account.tax.invoice.line'

    invoice_id = fields.Many2one('account.tax.invoice', string='Invoice Reference',
                                 ondelete='cascade', index=True)

    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice line')

