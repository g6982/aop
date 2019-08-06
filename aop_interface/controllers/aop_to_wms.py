# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
from .tools import validate_token, valid_response, invalid_response, extract_arguments
import logging
import json

_logger = logging.getLogger(__name__)


class AopToWms(http.Controller):

    @validate_token
    @http.route('/api/get_token_value', type='json', auth="none", methods=['POST'], csrf=False)
    def get_token_value(self, **kwargs):
        _logger.info({
            'kwargs': kwargs,
        })
        return valid_response('Success')

    @validate_token
    @http.route('/<string:model>/test_api', type='json', auth="none", methods=['POST'], csrf=False)
    def test_api(self, model=None, **post):
        warehouse_id = request.env['stock.warehouse'].search([], limit=1)
        return json.dumps({
            'name': warehouse_id.name,
            'id': warehouse_id.id,
            'model': model,
            'post': post
        })
