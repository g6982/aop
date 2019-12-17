# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InsuranceAopContract(models.Model):
    _inherit = 'aop.contract'
    _name = 'insurance.aop.contract'
    _description = u'保险合同'

    insurance_type_id = fields.Many2one('insurance.management.type', 'Type')
    purchase_id = fields.Many2one('res.partner')
    insurance_partner_id = fields.Many2one('res.partner')

    insurance_cover = fields.Char('Insurance cover')
    insurance_data = fields.Char('Insurance Data')

    excluding_deductible = fields.Boolean('Excluding deductible')

    contract_ids = fields.One2many('insurance.aop.contract.line', 'contract_id', 'Contract line')

    @api.multi
    def find_insurance_delivery_carrier_id(self, purchase_line_id):
        latest_carrier_id = self.find_insurance_carrier_line(purchase_line_id)

        if not latest_carrier_id:
            raise UserError('Can not find correct insurance contract !')

    def find_insurance_carrier_line(self, purchase_line_id):
        partner_id = purchase_line_id.partner_id

        now_date = fields.Datetime.now()
        res = self.env['insurance.aop.contract'].sudo().search([
            ('partner_id', '=', partner_id.id),
            ('contract_version', '!=', 0),
            ('date_start', '<', now_date),
            ('date_end', '>', now_date)
        ])

        carrier_id = self.env['insurance.aop.contract.line'].search([
            ('product_id', '=', purchase_line_id.transfer_product_id.id),
            ('contract_id', 'in', res.ids)
        ])
        _logger.info({
            'carrier_id': carrier_id
        })
        return carrier_id


class InsuranceLine(models.Model):

    _name = 'insurance.aop.contract.line'

    name = fields.Char('Name')

    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Brand')

    product_id = fields.Many2one('product.product', string='Product', domain=[('type', '=', 'product')])

    fixed_price = fields.Float(string='Fixed Price')

    contract_id = fields.Many2one('insurance.aop.contract', 'Contract')

