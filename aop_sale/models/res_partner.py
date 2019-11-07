# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 名字不重复的限制
    # 参考的限制
    _sql_constraints = [
        ('unique_name_parent_id', 'unique(name, parent_id)', 'the name and parent_id must be unique!'),
        ('unique_ref', 'unique(ref)', 'the ref must be unique!')
    ]

    kilometer_number = fields.Float('Kilometer')
    allow_warehouse_ids = fields.Many2many('stock.warehouse', string='Allowed warehouse')

    # 发送客户供应商的信息
    def send_res_partner_to_wms(self):
        data = []
        for line_id in self:
            data.append({
                'name': line_id.name,
                'code': line_id.ref,
                'country_name': line_id.country_id.name,
                'state_name': line_id.state_id.name,
                'city_name': line_id.city_id.name,
                'district_name': line_id.district_id.name,
                'street_name': line_id.street
            })

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        res.send_res_partner_to_wms()
        return res
