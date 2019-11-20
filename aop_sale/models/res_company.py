# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.stock.models.res_company import Company


class ResCompany(models.Model):
    _inherit = 'res.company'

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'the code must be unique')
    ]

    code = fields.Char('Code')

    # # 针对新建公司。不添加公司属性
    # @api.model
    # def create(self, vals):
    #     company = super(Company, self).create(vals)
    #
    #     company.create_transit_location()
    #     # mutli-company rules prevents creating warehouse and sub-locations
    #     self.env['stock.warehouse'].check_access_rights('create')
    #     data = {
    #         'name': company.name,
    #         'code': company.name[:5],
    #         'company_id': False,
    #         'partner_id': company.partner_id.id
    #     }
    #     # self.env['stock.warehouse'].sudo().create({'name': company.name, 'code': company.name[:5], 'company_id': company.id, 'partner_id': company.partner_id.id})
    #     self.env['stock.warehouse'].sudo().create(data)
    #     return company
