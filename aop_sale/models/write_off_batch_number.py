# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WriteOffBatchNUmber(models.Model):
    _name = 'write.off.batch.number'
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    handover_ids = fields.Many2many('handover.vin', string='Handover')

    invoice_line_ids = fields.Many2many('account.invoice.line', string='Invoice lines')
    state = fields.Selection([
        ('draft', 'draft'),
        ('verify', 'Verify'),
        ('done', 'Done'),
    ], default='draft')

    finance_verify_user_id = fields.Many2one('res.users', track_visibility='onchange')
    finance_verify_datetime = fields.Datetime('Finance verify time', track_visibility='onchange')

    @api.multi
    def finance_verify_handover(self):
        self.sudo().write({
            'state': 'verify',
            'finance_verify_user_id': self.env.user.id,
            'finance_verify_datetime': fields.Datetime.now()
        })

    @api.multi
    def cancel_finance_verify(self):
        for line in self:
            if line.state != 'verify':
                continue
            line.sudo().write({
                'state': 'draft',
                'finance_verify_user_id': False,
                'finance_verify_datetime': False
            })

    @api.multi
    def generate_account_invoice(self):
        for line in self:
            order_line_ids = line.handover_ids.mapped('order_line_id')

            context = {
                'active_ids': order_line_ids.ids,
                'write_off_batch_number_id': line.id,
                'handover_ids': line.handover_ids.ids
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

    # 退回
    @api.multi
    def return_to_register(self):
        context = {
            'write_off_batch_id': self.id,
            'select_handover_ids': self.handover_ids.ids
        }
        return {
            'name': _('Return'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'return.handover.wizard',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }
