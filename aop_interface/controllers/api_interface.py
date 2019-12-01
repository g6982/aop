# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
from .tools import validate_token, valid_response, invalid_response, extract_arguments
import logging
import json
import uuid
import time
from odoo.tools import config
from ..celery.aop_receive_from_wms import aop_receive_from_wms
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
        request.session.db = config.get('interface_db_name')

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

    @http.route('/api/barcode/<string:barcode>', type='http', auth="none", csrf=False)
    def test_api(self, barcode=None, **post):
        msg = {
            'code': 200,
        }
        _logger.info({
            'post': post,
            'barcode': barcode
        })
        return json.dumps(msg)

    @http.route('/api/warehouse/list', methods=["POST"], type='json', auth='none', csrf=False)
    def get_warehouse_list(self, **post):
        _logger.info({
            'post': post
        })
        request.session.db = config.get('interface_db_name')
        res = request.env['stock.warehouse'].sudo().search([])
        data = {}
        for index_w, warehouse_id in enumerate(res):
            data.update({
                index_w: warehouse_id.name
            })
        return json.dumps(data)

    @http.route('/api/stock_picking_type/list/<string:barcode>', methods=["POST"], type='json', auth='none', csrf=False)
    def get_stock_picking_type(self, barcode=None, **post):
        _logger.info({
            'post': post,
            'barcode': barcode
        })
        request.session.db = config.get('interface_db_name')
        res = request.env['stock.picking.type'].sudo().search([
            ('warehouse_id.name', '=', post.get('warehouse_name', False))
        ])
        data = {}
        for index_p, picking_type_id in enumerate(res):
            data.update({
                index_p: picking_type_id.name
            })
        return json.dumps(data)

    @http.route('/api/stock_picking_type/list_value', methods=["POST"], type='json', auth='none', csrf=False)
    def get_stock_picking_type_value(self, **post):
        request.session.db = config.get('interface_db_name')

        res = request.env['stock.picking.type'].sudo().search([
            ('warehouse_id', '!=', False)
        ], limit=10)
        data = {}
        for index_p, picking_type_id in enumerate(res):
            stock_picking_ids = request.env['stock.picking'].sudo().search([
                ('picking_type_id', '=', picking_type_id.id),
            ])
            data.update({
                index_p: picking_type_id.name + '/' + picking_type_id.warehouse_id.name + '/'
            })
        return json.dumps(data)

    @http.route('/api/stock_picking/list_value', methods=["POST"], type='json', auth='none', csrf=False)
    def get_stock_picking_ids_value(self, **post):
        request.session.db = config.get('interface_db_name')
        res = request.env['stock.picking'].sudo().search([
            ('state', '=', 'draft'),
        ])
        data = {}
        for index_p, picking_id in enumerate(res):
            value = picking_id.vin_id.name if picking_id.vin_id else str(time.time())
            data.update({
                index_p: picking_id.name + '|' + value
            })
        return json.dumps(data)

    @http.route('/api/stock_picking/list', methods=["POST"], type='json', auth='none', csrf=False)
    def get_stock_picking_ids(self, barcode=None, **post):
        _logger.info({
            'post': post,
            'barcode': barcode
        })
        request.session.db = config.get('interface_db_name')
        res = request.env['stock.picking'].sudo().search([
            ('state', '=', 'draft'),
            ('picking_type_id.name', '=', post.get('picking_type_name', False))
        ])
        data = {}
        for index_p, picking_type_id in enumerate(res):
            data.update({
                index_p: picking_type_id.name
            })
        return json.dumps(data)

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
        self._done_picking(post.get('data'))
        return json.dumps(msg)

    def _check_stock_picking(self, data):
        request.session.db = config.get('interface_db_name')
        if data:
            res = request.env['check.stock.picking.log'].sudo().create(data)
            return res

    def _done_picking(self, data):
        request.session.db = config.get('interface_db_name')

        # res = request.env['done.picking.log'].sudo().create(data)
        # return res

        username = config.misc.get("celery", {}).get('user_name')
        password = config.misc.get("celery", {}).get('user_password')
        url = config.misc.get("celery", {}).get('url')
        db_name = config.get('interface_db_name')
        model_name = 'done.picking.log'
        method_name = 'create'

        _logger.info({
            'data': data
        })
        # 放进celery 队列
        aop_receive_from_wms.delay(
            url=url,
            db=db_name,
            username=username,
            password=password,
            model=model_name,
            method=method_name,
            data=data
        )

