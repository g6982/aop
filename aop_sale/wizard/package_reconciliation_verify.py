# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import time
import hashlib
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PackageReconciliation(models.TransientModel):
    _name = 'package.reconciliation.wizard'

    name = fields.Char('Name')
    reconciliation_ids = fields.Many2many('reconciliation.file', string='Reconciliation list')

    batch_reconciliation_ids = fields.Many2many('batch.reconciliation.number')

    package_type = fields.Selection([
        ('re_file', 're_file'),
        ('batch_re', 'batch_re')
    ], string='Type')

    @api.model
    def default_get(self, fields_list):
        res = super(PackageReconciliation, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            current_model_name = self.env.context.get('current_model_name')
            _logger.info({
                'current_model_name': current_model_name
            })
            if current_model_name == 'reconciliation.file':
                res.update({
                    'reconciliation_ids': [(6, 0, self.env.context.get('active_ids'))],
                    'package_type': 're_file'
                })
            elif current_model_name == 'batch.reconciliation.number':
                res.update({
                    'batch_reconciliation_ids': [(6, 0, self.env.context.get('active_ids'))],
                    'package_type': 'batch_re'
                })
        return res

    # 打包批次号
    def package_reconciliation_list(self):
        re_line_ids = self.reconciliation_ids.mapped('re_line_ids')

        _logger.info({
            're_line_ids': re_line_ids,
            'invoice_line_ids': re_line_ids.mapped('invoice_line_id')
        })
        if any(getattr(x.invoice_line_id, 'id') is False for x in re_line_ids):
            raise UserError('Forbidden: You can not operate un-match records')

        invoice_line_ids = re_line_ids.mapped('invoice_line_id')
        if not invoice_line_ids:
            return False
        else:
            res = self.env['batch.reconciliation.number'].create({
                'name': self.name if self.name else hashlib.md5(str(re_line_ids).encode('UTF-8')).hexdigest().upper(),
                'invoice_line_ids': [(6, 0, invoice_line_ids.ids)],
                'reconciliation_file_ids': [(6, 0, self.reconciliation_ids.ids)]
            })

            # 对帐数据关联批次
            re_line_ids.write({
                'batch_reconciliation_id': res.id
            })

            invoice_line_ids.write({
                'verify_batch_id': res.id
            })

    # 审核
    def verify_reconciliation_list(self):
        # 对帐批次号
        batch_reconciliation_ids = self.batch_reconciliation_ids

        # 对帐数据
        reconciliation_file_ids = batch_reconciliation_ids.mapped('reconciliation_file_ids')

        invoice_line_ids = batch_reconciliation_ids.mapped('invoice_line_ids')
        data = {
            'name': self.name,
            'reconciliation_file_ids': [(6, 0, reconciliation_file_ids.ids)],
            'invoice_line_ids': [(6, 0, invoice_line_ids.ids)],
            'batch_reconciliation_ids': [(6, 0, batch_reconciliation_ids.ids)]
        }
        res = self.env['verify.batch.reconciliation'].create(data)

        # 批次里面关联审核
        batch_reconciliation_ids.write({
            'verify_batch_id': res.id
        })
        batch_reconciliation_ids.verify_account_invoice()
