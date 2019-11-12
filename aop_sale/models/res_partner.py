# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import logging
_logger = logging.getLogger(__name__)
import json
import time
from ..tools.zeep_client import zeep_supplier_client

SUPPLIER_FIELD_DICT = {
    'name': 'name',
    'ref': 'code',
    'country_id': 'country_name',
    'state_id': 'state_name',
    'city_id': 'city_name',
    'district_id': 'district_name',
    'street': 'street_name'
}


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

    property_stock_customer = fields.Many2one(
        'stock.location', string="Customer Location", company_dependent=False,
        help="The stock location used as destination when sending goods to this contact.")
    property_stock_supplier = fields.Many2one(
        'stock.location', string="Vendor Location", company_dependent=False,
        help="The stock location used as source when receiving goods from this contact.")

    property_account_payable_id = fields.Many2one('account.account', company_dependent=False,
                                                  string="Account Payable", oldname="property_account_payable",
                                                  domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
                                                  help="This account will be used instead of the default one as the payable account for the current partner",
                                                  required=True)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=False,
                                                     string="Account Receivable", oldname="property_account_receivable",
                                                     domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
                                                     help="This account will be used instead of the default one as the receivable account for the current partner",
                                                     required=True)

    # 发送客户供应商的信息
    def send_res_partner_to_wms(self):
        data = []
        for line_id in self:
            tmp = {}
            for key_id in SUPPLIER_FIELD_DICT.keys():
                if getattr(line_id, key_id):
                    key_value = getattr(line_id, key_id)
                    tmp.update({
                        SUPPLIER_FIELD_DICT.get(key_id): getattr(key_value, 'name') if hasattr(key_value, 'name') else key_value
                    })
            if tmp:
                data.append(tmp)
        zeep_supplier_client.service.supplier(str(data))

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        res.send_res_partner_to_wms()
        return res
