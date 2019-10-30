# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_compare, float_is_zero
import math
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    account_tax_invoice_id = fields.Many2one('account.tax.invoice', 'Account tax invoice')
    reconciliation_batch_no = fields.Char('Reconciliation batch no')

    account_batch_no = fields.Char(string='Account batch')

    account_period_id = fields.Many2one('account.period', string='Period', compute='_compute_period_id', store=True)

    tmp_estimate = fields.Float('Temporary estimate', compute='_compute_estimate_billing_receipt', store=True)
    pre_billing = fields.Float('Pre-billing', compute='_compute_estimate_billing_receipt', store=True)
    advance_receipt = fields.Float('Advance receipt', compute='_compute_estimate_billing_receipt', store=True)

    cost_passage = fields.Float('Cost Passage', compute='_compute_estimate_billing_receipt', store=True)

    verify_user = fields.Many2one('res.users', 'Verify user', track_visibility='onchange')
    verify_time = fields.Datetime('Verify time', track_visibility='onchange')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('account', 'Account Checking'),
        ('open', 'Open'),
        ('in_payment', 'In Payment'),
        ('reconciliation', 'Reconciliation'),
        ('invoice', 'Invoice'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    period_month = fields.Char('Period', compute='_compute_contract_period', store=True)

    # 根据合同的账期计算期间
    @api.multi
    def _compute_contract_period(self):
        for line_id in self:
            period_domain = [
                ('partner_id', '=', line_id.partner_id.id)
            ]
            res = self.env['account.invoice'].search(period_domain)
            res_period = res.filtered(lambda x: x.period_month)

            contract_period_month = self.get_contract_period_month(line_id)

            # 一个都没有。初始日期
            if not res_period:
                line_id.period_month = str(line_id.date_invoice.year) + '-' + str(line_id.date_invoice.month).zfill(2)
            else:
                # 已经存在，根据账期，判断是否在当前期间内，如果不在，计算为新的账期
                res_period_month = res_period.mapped('period_month')
                res_period_month = sorted(list(set(res_period_month)))

                new_period_month = self.get_new_period_month(res_period_month, contract_period_month, line_id.date_invoice)
                line_id.period_month = new_period_month

    # 客户合同 / 供应商合同， 账期
    def get_contract_period_month(self, invoice_id):
        search_domain = [('partner_id', '=', invoice_id.partner_id.id)]
        if invoice_id.type == 'out_invoice':
            res = self.env['customer.aop.contract'].search(search_domain)
        elif invoice_id.type == 'in_invoice':
            res = self.env['supplier.aop.contract'].search(search_domain)
        return res[0].period_month if res else 0

    def get_new_period_month(self, all_period_month, contract_month, invoice_date):
        all_period_month = sorted(all_period_month)
        invoice_year = invoice_date.year
        invoice_month = invoice_date.month
        invoice_month_period = str(invoice_year) + '-' + str(invoice_month).zfill(2)

        if invoice_month_period < all_period_month[0]:
            raise UserError('Error. {} {}'.format(invoice_month_period, all_period_month[0]))

        # 大于最后一条，大了多少？
        if invoice_month_period > all_period_month[-1]:
            last_all_period_month = all_period_month[-1]

            # 计算两个日期相差的月份
            month_differ = self.month_differ(last_all_period_month, invoice_date)

            # 计算相差了多少个周期，如果相差值小于contract_month, 则就在本月内
            if contract_month > month_differ:
                return all_period_month[-1]
            else:
                if contract_month == 0:
                    raise UserError('Error')

                # 如果相差的月份大于合同的日期
                diff_period = month_differ / contract_month

                next_period_month = self.next_year_month(last_all_period_month, math.ceil(diff_period) * contract_month)
                return next_period_month
        else:
            # 介于两者之间
            for index_p, period_value in enumerate(all_period_month):
                if index_p + 1 == len(all_period_month):
                    break
                if period_value <= invoice_month_period < all_period_month[index_p + 1]:
                    return period_value
            return all_period_month[-1]

    # 比较月份
    def month_differ(self, date1, date2):
        date1_year = int(date1.split('-')[0])
        date1_month = int(date1.split('-')[-1])
        month_differ = abs((date1_year - date2.year) * 12 + (date1_month - date2.month) * 1)
        return month_differ

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
        else:
            month_period_month += diff_number_month
        return str(month_period_year) + '-' + str(month_period_month).zfill(2)

    ###################################################################################################################
    ###################################################################################################################
    # 取消生成凭证
    @api.multi
    def action_move_create(self):
        return True

    # 取消生成凭证
    @api.multi
    def invoice_validate(self):
        for invoice in self.filtered(lambda invoice: invoice.partner_id not in invoice.message_partner_ids):
            invoice.message_subscribe([invoice.partner_id.id])

            # # Auto-compute reference, if not already existing and if configured on company
            # if not invoice.reference and invoice.type == 'out_invoice':
            #     invoice.reference = invoice._get_computed_reference()
            #
            # # DO NOT FORWARD-PORT.
            # # The reference is copied after the move creation because we need the move to get the invoice number but
            # # we need the invoice number to get the reference.
            # invoice.move_id.ref = invoice.reference
        self._check_duplicate_supplier_reference()

        self.filtered(lambda item: item.type == 'in_invoice').write({
                'state': 'reconciliation'
            })

        self.filtered(lambda item: item.type != 'in_invoice').write({
            'state': 'open'
        })

        return

        # if self.type == 'in_invoice':
        #     return self.write({
        #         'state': 'reconciliation'
        #     })
        # return self.write({'state': 'open'})

    # 取消支付
    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        res = super(AccountInvoice, self)._compute_residual()
        self.reconciled = False
    ###################################################################################################################
    ###################################################################################################################

    @api.multi
    def verify_reconciliation(self):
        for line in self:
            if line.state == 'reconciliation' and line.type == 'in_invoice':
                line.write({
                    'verify_user': self.env.user.id,
                    'verify_time': fields.Datetime.now(),
                    'state': 'invoice'
                })
            else:
                line.write({
                    'verify_user': self.env.user.id,
                    'verify_time': fields.Datetime.now(),
                    'state': 'reconciliation'
                })

    def cancel_verify_reconciliation(self):
        for line in self:
            if line.state == 'invoice' and line.type == 'in_invoice':
                line.write({
                    'verify_user': False,
                    'verify_time': False,
                    'state': 'reconciliation'
                })
            else:
                line.write({
                    'verify_user': False,
                    'verify_time': False,
                    'state': 'open'
                })

    # 检查月结
    @api.constrains('account_period_id', 'name')
    def _check_monthly_state(self):
        for line in self:
            if line.account_period_id.monthly_state:
                raise UserError(_('Has been monthly!'))

    @api.model
    def create(self, vals):
        self._check_monthly_state()
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, vals):
        self._check_monthly_state()
        return super(AccountInvoice, self).write(vals)

    # 删除的时候，删除 purchase.invoice.batch.no
    @api.multi
    def unlink(self):
        self._check_monthly_state()
        reconciliation_batch_no = self.mapped('reconciliation_batch_no')

        res = super(AccountInvoice, self).unlink()

        batch_ids = self.env['purchase.invoice.batch.no'].search([
            ('name', 'in', reconciliation_batch_no)
        ])
        for line in batch_ids:
            if not line.invoice_line_ids:
                line.unlink()

        self._null_invoice_order_line_data()
        return res

    # FIXME: 不知道为啥many2many 的值没有被删除
    def _null_invoice_order_line_data(self):
        sql_delete = '''
            delete from sale_order_line_invoice_rel where invoice_line_id not in (select id from account_invoice_line)
        '''
        self.env.cr.execute(sql_delete)
        self.env.cr.commit()

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


    @api.depends('invoice_line_ids.pre_billing', 'invoice_line_ids.tmp_estimate', 'invoice_line_ids.advance_receipt', 'invoice_line_ids.cost_passage')
    def _compute_estimate_billing_receipt(self):
        for line in self:
            line.pre_billing = sum(x.pre_billing for x in line.invoice_line_ids)
            line.tmp_estimate = sum(x.tmp_estimate for x in line.invoice_line_ids)
            line.advance_receipt = sum(x.advance_receipt for x in line.invoice_line_ids)
            line.cost_passage = sum(x.cost_passage for x in line.invoice_line_ids)

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

    # @api.model
    # def fields_get(self, allfields=None, attributes=None):
    #     res = super(AccountInvoiceLine, self).fields_get(allfields, attributes=attributes)
    #     # add reified groups fields
    #     # for app, kind, gs in self.env['res.groups'].sudo().get_groups_by_application():
    #     #    pass
    #     res["purchase_line_price"]["type"] = 'float'
    #     return res

    tax_invoice_amount = fields.Float('Tax invoice amount')
    tax_invoice_state = fields.Boolean('Tax invoice state', default=False)

    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale order line')
    line_price_subtotal = fields.Monetary(related='sale_order_line_id.price_subtotal', readonly=True)
    line_price_unit = fields.Float(related='sale_order_line_id.price_unit', readonly=True)

    from_location_id = fields.Many2one('res.partner', related='sale_order_line_id.from_location_id', readonly=True)
    to_location_id = fields.Many2one('res.partner', related='sale_order_line_id.to_location_id', readonly=True)

    location_id = fields.Many2one('stock.location', readonly=True)
    location_dest_id = fields.Many2one('stock.location', readonly=True)

    vin_id = fields.Many2one('stock.production.lot', 'VIN', related='sale_order_line_id.vin', readonly=True)
    contract_price = fields.Float('Contract price')
    purchase_line_price = fields.Monetary(related='purchase_line_id.price_subtotal', store=True, readonly=False)

    tmp_estimate = fields.Float('Temporary estimate')

    pre_billing = fields.Float('Pre-billing', compute='_compute_pre_billing', store=True)
    advance_receipt = fields.Float('Advance receipt',
                                   compute='_compute_advance_receipt',
                                   inverse='_set_advance_receipt',
                                   store=True)

    cost_passage = fields.Float('Cost Passage', compute='_compute_cost_passage', store=True)

    verify_batch_id = fields.Many2one('batch.reconciliation.number', string='Batch number', index=True)

    state = fields.Selection(related='invoice_id.state', readonly=True)

    @api.multi
    @api.depends('sale_order_line_id.stock_picking_ids', 'sale_order_line_id.stock_picking_ids.state')
    def _compute_pre_billing(self):
        for line in self:
            if line.invoice_id.type != 'out_invoice':
                continue
            if not line.sale_order_line_id:
                continue
            if not line.sale_order_line_id.stock_picking_ids:
                res = self.env['account.tax.invoice.line'].search([
                    ('invoice_line_id', '=', line.id)
                ])
                if not res:
                    continue
                line.pre_billing = sum(x.price_unit for x in res)
            else:
                if all(x.state == 'done' for x in line.sale_order_line_id.stock_picking_ids):
                    line.pre_billing = 0
                else:
                    res = self.env['account.tax.invoice.line'].search([
                        ('invoice_line_id', '=', line.id)
                    ])
                    if not res:
                        continue
                    line.pre_billing = sum(x.price_unit for x in res)

    @api.multi
    @api.depends('sale_order_line_id', 'sale_order_line_id.picking_confirm_date')
    def _compute_advance_receipt(self):
        for line in self:
            if line.invoice_id.account_period_id.monthly_state:
                continue
            if line.sale_order_line_id.picking_confirm_date:
                line.advance_receipt = 0

    def _set_advance_receipt(self):
        pass
        # for line in self:
        #     line.advance_receipt = line.advance_receipt

    # 在途成本:  采购订单"完成"<state:purchase>
    # 但是销售订单任务未完成的, 月结操作后值被锁定不会改变, 月结操作之前, 这一列的值会变化, 如果销售订单任务完成了, 该列的值会变为0.
    @api.multi
    @api.depends('sale_order_line_id', 'purchase_line_id',
                 'sale_order_line_id.state', 'purchase_line_id.state', 'price_unit')
    def _compute_cost_passage(self):
        for line in self:
            if not line.invoice_id.account_period_id.monthly_state:
                if line.sale_order_line_id.picking_confirm_date:
                    line.cost_passage = 0
                elif line.purchase_line_id.state == 'purchase':
                    line.cost_passage = line.price_unit

    @api.model
    def create(self, vals):
        self.mapped('invoice_id')._check_monthly_state()
        return super(AccountInvoiceLine, self).create(vals)

    @api.multi
    def write(self, vals):
        self.mapped('invoice_id')._check_monthly_state()
        return super(AccountInvoiceLine, self).write(vals)

    @api.multi
    def unlink(self):
        self.mapped('invoice_id')._check_monthly_state()
        return super(AccountInvoiceLine, self).unlink()
