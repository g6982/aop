# -*- coding: utf-8 -*-
from collections import namedtuple
from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    parent_warehouse_id = fields.Many2one(
        'stock.warehouse', '上级仓库', index=True, ondelete='cascade')