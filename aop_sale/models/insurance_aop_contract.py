# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class InsuranceAopContract(models.Model):
    _inherit = 'aop.contract'
    _name = 'insurance.aop.contract'
    _description = u'保险合同'

    contract_ids = fields.One2many('insurance.aop.contract.line', 'contract_id', 'Contract line')


class InsuranceLine(models.Model):

    _name = 'insurance.aop.contract.line'

    name = fields.Char('Name')

    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Brand')

    product_id = fields.Many2one('product.product', string='Product', domain=[('type', '=', 'product')])

    fixed_price = fields.Float(string='Fixed Price')

    contract_id = fields.Many2one('insurance.aop.contract', 'Contract')

