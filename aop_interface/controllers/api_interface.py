# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
from .tools import validate_token, valid_response, invalid_response, extract_arguments
import logging
import json
import time

_logger = logging.getLogger(__name__)


class ApiInterface(http.Controller):

    @validate_token
    @http.route('/<string:model>/test_api', type='json', auth="none", methods=['POST'], csrf=False)
    def test_api(self, model=None, **post):
        picking_data = self.format_stock_picking_data()
        msg = {
            'code': 200,
            'data': picking_data
        }
        return json.dumps(msg)

    def format_stock_picking_data(self):
        picking_ids = request.env['stock.picking'].sudo().search([])
        data = []
        for picking_id in picking_ids:
            data.append({
                'task_id': picking_id.id,
                'partner_id': picking_id.partner_id.name,
                'vin': picking_id.vin_id.name,
                'product_id': picking_id.mapped('move_line_ids').mapped('product_id')[0].name,
                'from_location_id': picking_id.location_id.name,
                'to_location_id': picking_id.location_dest_id.name,
                'picking_type_id': picking_id.picking_type_id.name,
                'quantity_done': 1,
                'warehouse_id': picking_id.picking_type_id.warehouse_id.name
            })
        return data

    # @http.route('/api/barcode/<string:barcode>', type='http', auth="none", csrf=False)
    # def test_api(self, barcode=None, **post):
    #     msg = {
    #         'code': 200,
    #     }
    #     _logger.info({
    #         'post': post,
    #         'barcode': barcode
    #     })
    #     return json.dumps(msg)

    @validate_token
    @http.route('/api/sale_order/check_stock_picking', methods=["POST"], type='json', auth='none', csrf=False)
    def check_stock_picking(self, **post):
        msg = {
            'code': 200,
            'method': '/api/sale_order/check_stock_picking',
            'time': time.time()
        }

        self._check_stock_picking(post)
        return json.dumps(msg)

    @validate_token
    @http.route('/api/stock_picking/done_picking', methods=["POST"], type='json', auth='none', csrf=False)
    def done_picking(self, **post):
        msg = {
            'code': 200,
            'method': '/api/stock_picking/done_picking',
            'time': time.time(),
        }
        self._done_picking(post)
        return json.dumps(msg)

    def _check_stock_picking(self, data):
        res = request.env['check.stock.picking.log'].sudo().create(data)
        return res

    def _done_picking(self, data):
        res = request.env['done.picking.log'].sudo().create(data)
        return res
