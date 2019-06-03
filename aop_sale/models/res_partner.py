# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import traceback
import logging


class Partner(models.Model):
    _inherit = ['res.partner']

    type = fields.Selection(selection_add=[('take', 'Take Car Address')])
