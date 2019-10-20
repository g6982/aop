# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WriteOffBatchNUmber(models.Model):
    _name = 'write.off.batch.number'

    name = fields.Char('Name')
    handover_ids = fields.Many2many('handover.vin', string='Handover')

    invoice_line_ids = fields.Many2many('account.invoice.line', string='Invoice lines')

    @api.multi
    def generate_account_invoice(self):
        for line in self:
            order_line_ids = line.handover_ids.mapped('order_line_id')

            context = {
                'active_ids': order_line_ids.ids,
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

