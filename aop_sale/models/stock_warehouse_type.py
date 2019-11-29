# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class StockWarehouseType(models.Model):
    _name = 'stock.warehouse.type'

    name = fields.Char('Name')
