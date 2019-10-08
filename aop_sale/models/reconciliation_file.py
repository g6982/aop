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

    @api.multi
    def reconciliation_account_invoice(self):
        for line in self:
            invoice_line_id = self.env['account.invoice.line'].search([
                ('sale_order_line_id.handover_number', '=', line.name),
                ('sale_order_line_id.product_id', '=', line.product_id.id)
            ])

    @api.model
    def create(self, vals):
        res = super(ReconciliationFile, self).create(vals)
        self.reconciliation_account_invoice()
        return res
