# -*- coding: utf-8 -*-

from odoo.http import request
from odoo import http
import simplejson
import logging

_logger = logging.getLogger(__name__)


class SatementReportOrder(http.Controller):

    @http.route(['/report/aop_sale.standard_statement_report'], type='http', auth='user', multilang=True)
    def standard_statement_report(self, **data):
        _logger.info({
            'data': data
        })