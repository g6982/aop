# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReconciliationFile(models.Model):
    _name = 'reconciliation.file'

    name = fields.Char('Name')
    # batch_no = fields.Char('Batch no')
    batch_no = fields.Many2one('reconciliation.file.lot', string='Batch no')
    apply_no = fields.Char('Apply')
    transfer_way = fields.Char('Transfer')
    number = fields.Integer('Number')
    price_unit = fields.Float('Price unit')
    price_total = fields.Float('Price total')
    product_id = fields.Many2one('product.product', 'Product')

    re_line_ids = fields.One2many('reconciliation.file.line', 're_file_id', ondelete='cascade')

    reconciliation_state = fields.Selection(
        [('order_invoice', 'order_invoice'),
         ('order_only', 'order_only'),
         ('failed', 'failed')
         ],
        'Reconciliation state',
        compute='_compute_reconciliation_state',
        store=True)

    batch_reconciliation_id = fields.Many2one('batch.reconciliation.number', 'Batch reconciliation', index=True)

    @api.multi
    def confirm_account_invoice(self):
        for line in self:

            invoice_line_ids = line.re_line_ids.mapped('invoice_line_id')

            # 对账：需要将单车价格写入确认价格
            for account_invoice_line_id in invoice_line_ids:
                account_invoice_line_id.price_unit = line.price_unit

            # TODO: 如果 单车价格和合同价格相同，则对账 ?
            # invoice_line_id = invoice_line_id.filtered(lambda x: x.price_unit == x.contract_price)

            invoice_ids = invoice_line_ids.mapped('invoice_id')
            ids = list(set(invoice_ids.ids))
            invoice_ids = self.env['account.invoice'].browse(ids)

            for invoice_id in invoice_ids:
                invoice_id.action_invoice_open()

    @api.multi
    @api.depends('re_line_ids', 're_line_ids.invoice_line_id', 're_line_ids.sale_order_line_id')
    def _compute_reconciliation_state(self):
        for line in self:
            if not line.re_line_ids:
                line.reconciliation_state = 'failed'
            else:
                if any(getattr(x.invoice_line_id, 'id') is False for x in line.re_line_ids):
                    line.reconciliation_state = 'order_only'
                else:
                    if len(set(line.re_line_ids.mapped('sale_order_line_id'))) != line.number:
                        line.reconciliation_state = 'order_only'
                    else:
                        line.reconciliation_state = 'order_invoice'

    @api.multi
    def reconciliation_account_invoice(self):
        for line in self:
            sale_order_line_ids = self.env['sale.order.line'].search([
                ('handover_number', '=', line.name),
                ('product_id', '=', line.product_id.id),
            ], limit=line.number)

            if not sale_order_line_ids:
                continue

            not_invoice_line = sale_order_line_ids.filtered(lambda x: not x.invoice_lines)

            # 筛选过滤
            if line.batch_no.mapped('invoice_line_ids') if line.batch_no else False:
                invoice_line_ids = list(set(sale_order_line_ids.mapped('invoice_lines')) & set(line.batch_no.mapped('invoice_line_ids')))
            else:
                invoice_line_ids = sale_order_line_ids.mapped('invoice_lines')

            data = []
            for invoice_id in invoice_line_ids:
                data.append((0, 0, {
                    'sale_order_line_id': invoice_id.sale_order_line_id.id,
                    'invoice_line_id': invoice_id
                }))
            for line_id in not_invoice_line:
                data.append((0, 0, {
                    'invoice_line_id': False,
                    'sale_order_line_id': line_id.id
                }))
            if data:
                line.re_line_ids = False
                line.re_line_ids = data
            else:
                line.re_line_ids = False

        for batch_id in list(set(self.mapped('batch_no'))):
            if batch_id.mapped('reconciliation_ids').mapped('re_line_ids') if batch_id.mapped('reconciliation_ids') else False:
                un_invoice_line_ids = list(set(batch_id.mapped('invoice_line_ids')) - set(
                    batch_id.mapped('reconciliation_ids').mapped('re_line_ids').mapped('invoice_line_id')))
            else:
                un_invoice_line_ids = batch_id.mapped('invoice_line_ids')
            if un_invoice_line_ids:
                batch_id.un_invoice_line_ids = [(6, 0, [x.id for x in un_invoice_line_ids])]
            else:
                batch_id.un_invoice_line_ids = False

    def fill_reconciliation_lot(self):
        for line in self:
            line.batch_no.write({
                'reconciliation_ids': [(4, line.id)]
            })


class ReconciliationFileLine(models.Model):
    _name = 'reconciliation.file.line'

    re_file_id = fields.Many2one('reconciliation.file', required=True, ondelete='cascade')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', domain=[('type', '=', 'out_invoice')])
    price_unit = fields.Float(related='invoice_line_id.price_unit')
    reconciliation_price_unit = fields.Float(related='re_file_id.price_unit')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order line')

    state = fields.Selection(
        [('success', 'Success'),
         ('price_error', 'Price Error')
         ],
        'state',
        default='none',
        compute='_compute_state',
        store=True)

    error_type = fields.Selection(
        [('contract_price_error', 'Contract Price Error'),
         ('customer_price_error', 'Customer Price Error')
         ],
        'Error Type')

    @api.multi
    @api.depends('price_unit', 'reconciliation_price_unit')
    def _compute_state(self):
        for line in self:
            if line.price_unit != line.reconciliation_price_unit:
                line.state = 'price_error'


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    @api.multi
    def do(self, fields, columns, options, dryrun=False):
        res = super(BaseImport, self).do(fields, columns, options, dryrun)

        if not dryrun and self.res_model == 'reconciliation.file':
            records = self.env['reconciliation.file'].browse(res.get('ids'))
            records.fill_reconciliation_lot()
            # records.reconciliation_account_invoice()
        return res


class ReconciliationFileLot(models.Model):
    _name = 'reconciliation.file.lot'
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'the name must be unique!')
    ]

    name = fields.Char('Name')
    invoice_line_ids = fields.Many2many(
        'account.invoice.line',
        'reconciliation_file_lot_invoice_line_ids',
        string='Invoice lines',
        domain=[('invoice_type', '=', 'out_invoice')]
    )
    un_invoice_line_ids = fields.Many2many(
        'account.invoice.line',
        'reconciliation_file_lot_not_invoice_line_ids',
        string='Invoice lines(NO)',
        domain=[('invoice_type', '=', 'out_invoice')]
    )
    reconciliation_ids = fields.Many2many('reconciliation.file', string='Reconciliation ids', ondelete='cascade')

    def reconciliation_account_invoice(self):
        self.mapped('reconciliation_ids').reconciliation_account_invoice()


# class ReconciliationFileLotLine(models.Model):
#     _name = 'reconciliation.file.lot.line'
#     _sql_constraints = [
#         ('unique_name', 'unique(name)', 'the name must be unique!')
#     ]
#
#     name = fields.Char('Name')
#     file_lot_id = fields.Many2one('reconciliation.file.lot')
#     invoice_line_ids = fields.Many2one('account.invoice.line', string='Invoice lines')
#     # reconciliation_state = fields.Boolean('Reconciliation state')
