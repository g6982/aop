# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # 添加服务产品到stock.picking
    def _get_custom_move_fields(self):
        res = super(StockRule, self)._get_custom_move_fields()
        res.append('service_product_id')
        return res
