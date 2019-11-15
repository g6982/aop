# -*- coding: utf-8 -*-

from odoo import models, fields, api

FIELD_LIST = ['picking_id', 'mass_attachment_ids']


class MassLossOrder(models.Model):
    _name = 'mass.loss.order'
    _inherit = ['mail.thread']
    _description = 'Mass Loss Order'

    name = fields.Char('Mass Loss Name')
    vin_code = fields.Char('VIN')
    box_no = fields.Char('Box no')
    brand_id = fields.Many2one('fleet.vehicle.model.brand')
    date = fields.Date('Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('apply', 'Apply'),
        ('approval', 'Approval'),
        ('done', 'Done')
    ], default='draft')

    found_department = fields.Many2one('res.partner', 'found department')
    originator = fields.Many2one('res.partner', 'originator')
    responsible_department = fields.Many2one('res.partner', 'responsible department')
    responsible_party = fields.Many2one('res.partner', 'responsible party')
    filing_fee = fields.Float('Filing fee')
    approval_fee = fields.Float('Approval fee')
    mass_loss_part = fields.Many2one('mass.loss.part', 'Mass Loss part')
    mass_loss_type = fields.Many2one('mass.loss.type')
    task_no = fields.Char('Task no')
    order_no = fields.Char('Order no')
    task_content = fields.Char('Task Content')
    create_user = fields.Many2one('res.users', 'Creator')
    approval_user = fields.Many2one('res.users', 'Approval user')
    confirm_user = fields.Many2one('res.users', 'Confirm user')
    confirm_time = fields.Datetime('Confirm Time')
    note = fields.Text('Note')
    close_user = fields.Many2one('res.users', 'Closer')
    close_time = fields.Datetime('Close Time')
    approval_opinion = fields.Text('Approval Options')
    payment_amount = fields.Float('Payment Amount')
    balance = fields.Float('Balance')
    debit_balance = fields.Float('Debit Balance')
    buyout_price = fields.Float('Buyout Price')
    guide_price = fields.Float('Guide Price')
    buyout_deductions_diff = fields.Float('Buyout deductions')
    case_number = fields.Char('Case Number')

    picking_id = fields.Many2one('stock.picking', 'Picking')
    mass_attachment_ids = fields.Many2many('mass.loss.attachment.template', string='Mass Attachment')

    insurance_price = fields.Float(string='insurance Price', compute='_compute_insurance_price', store=True)

    @api.multi
    @api.depends('vin_code', 'brand_id')
    def _compute_insurance_price(self):
        for line in self:
            if line.vin_code and line.brand_id:
                search_domain = [('vin_code', '=', line.vin_code)]
                sale_order_line = self.env['sale.order.line'].search(search_domain, limit=1)

                if sale_order_line:
                    search_domain = [
                                        ('product_id', '=', sale_order_line.product_id.id),
                                        ('brand_id', '=', line.brand_id.id)
                                     ]
                    insurance_aop_contract_line_id = self.env['insurance.aop.contract.line'].search(search_domain, limit=1)

                    line.insurance_price = insurance_aop_contract_line_id.fixed_price if insurance_aop_contract_line_id else 0

                    return

            line.insurance_price = 0



    @api.multi
    def action_return_to_factory(self):
        pass

    @api.model
    def default_get(self, filed_list):
        res = super(MassLossOrder, self).default_get(filed_list)
        for filed_name in FIELD_LIST:
            if self.env.context.get(filed_name, False):
                res[filed_name] = self.env.context.get(filed_name)
        return res


class MassLossType(models.Model):
    _name = 'mass.loss.type'
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Type name must unique')
    ]

    name = fields.Char('Mass Loss Type')


class MassLossPart(models.Model):
    _name = 'mass.loss.part'
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Part name must unique')
    ]

    name = fields.Char('Mass Loss Part')


class MassLossAttachment(models.Model):
    _name = 'mass.loss.attachment.template'

    name = fields.Char('Name')
    files = fields.Many2many('ir.attachment')
