# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import logging
_logger = logging.getLogger(__name__)
import json
import time
from odoo.tools import config
from ..tools.zeep_client import get_zeep_client_session

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

    property_account_payable_id = fields.Many2one(
        'account.account', company_dependent=False,
        default=lambda self: self.env['account.account'].search(
            [('internal_type', '=', 'payable'), ('deprecated', '=', False)],
            limit=1).id,
        string="Account Payable", oldname="property_account_payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True)
    property_account_receivable_id = fields.Many2one(
        'account.account', company_dependent=False,
        default=lambda self: self.env['account.account'].search(
            [('internal_type', '=', 'receivable'),
             ('deprecated', '=', False)], limit=1).id,
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
        supplier_url = self.env['ir.config_parameter'].sudo().get_param('aop_interface.partner_url', False)

        # 获取 session, 发送数据
        zeep_supplier_client = get_zeep_client_session(supplier_url)
        zeep_supplier_client.service.supplier(str(data))

    @api.model_create_multi
    def create(self, vals):
        res = super(ResPartner, self).create(vals)

        # 如果是系统导入，则不需要进行这一步
        if not self._context.get('import_file'):
            supplier_state = self.env['ir.config_parameter'].sudo().get_param('aop_interface.enable_partner', False)

            # 先判断是否启用
            if supplier_state and config.get('enable_aop_interface'):
                res.send_res_partner_to_wms()
        return res

    # # TODO: 对用户进行分类，客户，供应商，仓库的合作伙伴，用户的合作伙伴，位置的合作伙伴，公司的合作伙伴
    # user_usage_type = fields.Selection([
    #     ('warehouse_type', 'Warehouse type'),
    #     ('location_type', 'Location type'),
    #     ('customer_type', 'Customer type'),
    #     ('supplier_type', 'Supplier type'),
    #     ('user_type', 'User type'),
    #     ('company_type', 'Company type')
    # ], default=False)


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    @api.multi
    def do(self, fields, columns, options, dryrun=False):
        res = super(BaseImport, self).do(fields, columns, options, dryrun)

        if not dryrun and self.res_model == 'res.partner':
            records = self.env['res.partner'].browse(res.get('ids'))

            supplier_state = self.env['ir.config_parameter'].sudo().get_param('aop_interface.enable_partner', False)
            if supplier_state and config.get('enable_aop_interface'):
                records.send_res_partner_to_wms()
            # records.reconciliation_account_invoice()
        return res
