# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BatchPurchaseInvoiceLine(models.TransientModel):
    _name = 'batch.purchase.invoice.line.wizard'

    name = fields.Char('Name')
    invoice_line_ids = fields.Many2many('account.invoice.line')

    @api.model
    def default_get(self, fields_list):
        res = super(BatchPurchaseInvoiceLine, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            invoice_line_ids = self.env['account.invoice.line'].browse(self.env.context.get('active_ids'))
            # 是否需要判断过滤？
            done_invoice_ids = self.env['purchase.batch.invoice.line'].search([])

            invoice_line_ids = list(set(invoice_line_ids.ids) - set(done_invoice_ids.mapped('invoice_line_id').ids))
            res.update({
                'invoice_line_ids': [(6, 0, invoice_line_ids)]
            })
        return res

    def generate_batch_invoice(self):
        if not self.invoice_line_ids:
            raise UserError('Error!')

        res = self.env['purchase.batch.invoice'].create({
            'name': self.name,
            'batch_line_ids': [(0, 0, {
                'invoice_line_id': x.id
            }) for x in self.invoice_line_ids]
        })

        view_id = self.env.ref('aop_sale.view_purchase_batch_invoice_tree').id
        form_id = self.env.ref('aop_sale.view_purchase_batch_invoice_form').id

        # 跳转到导入成功后的tree界面
        return {
            'name': _('Batch purchase invoice'),
            'view_type': 'form',
            'view_id': False,
            'views': [(view_id, 'tree'), (form_id, 'form')],
            'res_model': 'purchase.batch.invoice',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res.ids)],
            'limit': 80,
            'target': 'current',
        }
