# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class InsuranceManagement(models.Model):
    _name = 'insurance.management'
    _description = u'保险管理'

    name = fields.Char('Name')
    insurance_type_id = fields.Many2one('insurance.management.type', 'Type')
    purchase_id = fields.Many2one('res.partner')
    insurance_partner_id = fields.Many2one('res.partner')

    insurance_cover = fields.Char('Insurance cover')
    insurance_data = fields.Char('Insurance Data')

    excluding_deductible = fields.Boolean('Excluding deductible')


class InsuranceManagementType(models.Model):
    _name = 'insurance.management.type'

    name = fields.Char('Name')
