# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
import binascii
import traceback
import re

_logger = logging.getLogger(__name__)


class MonthClose(models.TransientModel):
    _name = 'month.close.wizard'

    period_id = fields.Many2one('account.period', string='Period')

    def start_generate_monthly(self):
        pass

    def cancel_monthly(self):
        pass
