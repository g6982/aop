# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReconciliationFile(models.Model):
    _name = 'reconciliation.file'

    name = fields.Char('Name')
    batch_no = fields.Char('Batch no')
    apply_no = fields.Char('Apply')
    transfer_way = fields.Char('Transfer')
    number = fields.Integer('Number')
    price_unit = fields.Float('Price unit')
    price_total = fields.Float('Price total')
    product_id = fields.Many2one('product.product', 'Product')

    re_line_ids = fields.One2many('reconciliation.file.line', 're_file_id')

    reconciliation_state = fields.Selection(
        [('order_invoice', 'order_invoice'),
         ('order_only', 'order_only'),
         ('failed', 'failed')
         ],
        'Reconciliation state',
        compute='_compute_reconciliation_state',
        store=True)

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
                _logger.info({
                    'any(x.invoice_line_id is False for x in line.re_line_ids)': any(x.invoice_line_id is False for x in line.re_line_ids)
                })
                if any(getattr(x.invoice_line_id, 'id') is False for x in line.re_line_ids):
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
            data = []
            for invoice_id in sale_order_line_ids.mapped('invoice_lines'):
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


class ReconciliationFileLine(models.Model):
    _name = 'reconciliation.file.line'

    re_file_id = fields.Many2one('reconciliation.file')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order line')


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    @api.multi
    def do(self, fields, columns, options, dryrun=False):
        res = super(BaseImport, self).do(fields, columns, options, dryrun)

        if not dryrun and self.res_model == 'reconciliation.file':
            records = self.env['reconciliation.file'].browse(res.get('ids'))
            records.reconciliation_account_invoice()
        return res