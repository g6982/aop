# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AopContract(models.Model):
    _name = 'aop.contract'
    _description = 'AOP contract'

    name = fields.Char('name', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    serial_number = fields.Char(string='Contract number')
    version_id = fields.Many2one('contract.version', string="Version")
    serial_no = fields.Char(string='Contract no')
    is_formal = fields.Boolean(string='Contract', default=True)
    project_id = fields.Many2one('contract.project', string="Project")
    date_start = fields.Date('Start date', required=True, default=fields.Date.today)
    date_end = fields.Date('End date')
    effective_date = fields.Date('Active date')
    expiry_date = fields.Date('Expire_date')
    source = fields.Char(string='Source')
    type = fields.Selection(
        [
            ('buyer', 'Buyer'),
            ('supplier', 'Supplier')
        ],
        string='Contract type',
        default='buyer')
    delivery_carrier_ids = fields.One2many('delivery.carrier', 'contract_id', string="Contract terms")
    aging = fields.Float('Aging(day)', default=1)


class ContractVersion(models.Model):
    _name = 'contract.version'

    name = fields.Char(string='Version')


class ContractProject(models.Model):
    _name = 'contract.project'

    name = fields.Char(string='Project')

