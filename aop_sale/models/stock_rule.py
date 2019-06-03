# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import traceback
import logging



_logger = logging.getLogger(__name__)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _get_rule(self, product_id, location_id, values):

       values.update({'warehouse_id': False})

       return super(ProcurementGroup, self)._get_rule(product_id, location_id, values)


#class BundleStockRule(models.Model):
#    _name = 'bundle.stock.rule'

#    name = fields.Char('名称', required=True)

#    service_product_id = fields.Many2one('product.product', string='服务产品', domain=[('purchase_ok', '=', '')])

#    rule_ids = fields.Many2many(
#        comodel_name='stock.rule',  # related model
#        relation='stock_rule_bundle_rel',  # relation table name
#        column1='rule_id',  # field for "this" record
#        column2='bundle_id',  # field for "other" record
#        string='规则组')


