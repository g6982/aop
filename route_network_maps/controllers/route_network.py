# -*- coding: utf-8 -*-

from odoo.addons.web.controllers import main as report
from odoo.http import content_disposition, route, request
from odoo import http
import json
import logging

from ..tools.utils import geo_lines

_logger = logging.getLogger(__name__)


class RouteNetworkMaps(http.Controller):

    @http.route('/api/location/get_map_dir_line', type='http', auth="public", csrf=False)
    def get_map_dir_line(self, **post):
        chart_result = geo_lines()
        _logger.info({
            'chart_result': chart_result
        })
        print('chart_result: ', chart_result)
        return chart_result
