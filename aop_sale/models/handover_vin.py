# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HandoverVin(models.Model):
    _name = 'handover.vin'
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    vin_code = fields.Char('VIN')

    order_line_id = fields.Many2one('sale.order.line', compute='_compute_sale_order_line', store=True)
    write_user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    write_datetime = fields.Datetime('Write time', default=fields.Datetime.now())

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    verify_user_id = fields.Many2one('res.users')
    verify_datetime = fields.Datetime('Verify time')

    @api.multi
    @api.depends('name')
    def _compute_sale_order_line(self):
        order_line_obj = self.env['sale.order.line']
        for line in self:
            tmp = order_line_obj.search([('vin_code', '=', line.vin_code)])
            if not tmp:
                continue

            if len(tmp) > 1:
                raise UserError('More than one records!')

            line.order_line_id = tmp.id
            tmp.handover_number = line.name

    def verify_handover(self):
        pass

    def cancel_verify_handover(self):
        pass
