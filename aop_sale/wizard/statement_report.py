# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import random

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StatementReport(models.TransientModel):
    _name = 'invoice.order.statement.wizard'

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    def get_statement_report(self):

        sale_order = self.env['sale.order'].search([])
        datas = {
            'ids': self.ids,
            'model': self._name,
            'record': sale_order.ids,
        }
        report_name = 'aop_sale.standard_statement_report_xlsx'

        return self.env.ref(report_name).report_action(self, data=datas)
