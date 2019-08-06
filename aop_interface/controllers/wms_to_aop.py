# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
import functools
import logging
from .tools import validate_token, valid_response, invalid_response, extract_arguments
from odoo import http

_logger = logging.getLogger(__name__)



class WmsToAop(http.Controller):
    pass
