# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HandoverVin(models.Model):
    _name = 'handover.vin'
    _inherit = ['mail.thread']

    # 名字(交接单号)和vin不重复的限制
    _sql_constraints = [
        ('unique_name_vin_code', 'unique(name, vin_code)', 'the name and vin_code must be unique!')
    ]

    name = fields.Char('Handover number', track_visibility='onchange')
    vin_code = fields.Char('VIN', track_visibility='onchange')

    order_line_id = fields.Many2one('sale.order.line', compute='_compute_sale_order_line', store=True)
    write_user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    write_datetime = fields.Datetime('Write time', default=fields.Datetime.now())

    state = fields.Selection([
        ('draft', 'Draft'),
        ('register', 'Register'),
        ('done', 'Audit'),
        ('verify', 'Finance verify')
    ], default='draft', track_visibility='onchange')

    register_user_id = fields.Many2one('res.users', track_visibility='onchange')
    register_datetime = fields.Datetime('register time', track_visibility='onchange')

    verify_user_id = fields.Many2one('res.users', track_visibility='onchange')
    verify_datetime = fields.Datetime('Verify time', track_visibility='onchange')

    finance_verify_user_id = fields.Many2one('res.users', track_visibility='onchange')
    finance_verify_datetime = fields.Datetime('Finance verify time', track_visibility='onchange')

    file_planned_date = fields.Date('Planned date', related='order_line_id.file_planned_date', readonly=True)
    to_location_id = fields.Many2one('res.partner', related='order_line_id.to_location_id', readonly=True)

    @api.multi
    @api.depends('name')
    def _compute_sale_order_line(self):
        order_line_obj = self.env['sale.order.line']
        for line in self:
            tmp = order_line_obj.search(['|', ('vin_code', '=', line.vin_code), ('vin.name', '=', line.vin_code)])
            if not tmp:
                continue

            # 筛选没有交接单的
            tmp = tmp.filtered(lambda x: not x.handover_number)

            if len(tmp) > 1:
                raise UserError('More than one records!')

            tmp.write({
                'handover_number': line.name
            })
            line.order_line_id = tmp.id

    @api.multi
    def register_handover(self):
        self.ensure_one()
        res = self.env['handover.vin'].search([
            ('name', '=', self.name),
            ('state', '=', 'draft')
        ])
        res.sudo().write({
            'state': 'register',
            'register_user_id': self.env.user.id,
            'register_datetime': fields.Datetime.now()
        })

    @api.multi
    def verify_handover(self):
        self.ensure_one()
        res = self.env['handover.vin'].search([
            ('name', '=', self.name),
            ('state', '=', 'register')
        ])
        res.sudo().write({
            'state': 'done',
            'verify_user_id': self.env.user.id,
            'verify_datetime': fields.Datetime.now()
        })

    @api.multi
    def cancel_verify_handover(self):
        self.ensure_one()
        res = self.env['handover.vin'].search([
            ('name', '=', self.name),
            ('state', 'in', ['register', 'done'])
        ])
        res.sudo().write({
            'state': 'draft',
            'verify_user_id': False,
            'verify_datetime': False
        })

    @api.multi
    def finance_verify_handover(self):
        self.ensure_one()
        res = self.env['handover.vin'].search([
            ('name', '=', self.name),
            ('state', '=', 'done')
        ])
        res.sudo().write({
            'state': 'verify',
            'finance_verify_user_id': self.env.user.id,
            'finance_verify_datetime': fields.Datetime.now()
        })

    @api.multi
    def cancel_finance_verify(self):
        self.ensure_one()
        res = self.env['handover.vin'].search([
            ('name', '=', self.name),
            ('state', '=', 'verify')
        ])
        res.sudo().write({
            'state': 'done',
            'finance_verify_user_id': False,
            'finance_verify_datetime': False
        })
