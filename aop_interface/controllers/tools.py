# -*- coding: utf-8 -*-
import functools
import logging

from odoo.tools import config
from odoo import http
import werkzeug.wrappers
from odoo.http import request

_logger = logging.getLogger(__name__)
try:
    import simplejson as json
    from simplejson.errors import JSONDecodeError
except ImportError as identifier:
    _logger.error(identifier)


def valid_response(data, status=200):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {"code": status, "data": data}
    return json.dumps(data)


def invalid_response(typ, message=None, status=401):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    # return json.dumps({})
    return json.dumps(
        {
            "code": status,
            "type": typ,
            "message": str(message)
            if str(message)
            else "wrong arguments (missing validation)",
        }
    )


def extract_arguments(payloads, offset=0, limit=0, order=None):
    """."""
    fields, domain, payload = [], [], {}
    data = str(payloads)[2:-2]
    try:
        payload = json.loads(data)
    except JSONDecodeError as e:
        _logger.error(e)
    if payload.get("domain"):
        for _domain in payload.get("domain"):
            l, o, r = _domain
            if o == "': '":
                o = "="
            elif o == "!': '":
                o = "!="
            domain.append(tuple([l, o, r]))
    if payload.get("fields"):
        fields += payload.get("fields")
    if payload.get("offset"):
        offset = int(payload["offset"])
    if payload.get("limit"):
        limit = int(payload.get("limit"))
    if payload.get("order"):
        order = payload.get("order")
    return [domain, fields, offset, limit, order]


def validate_token(func):
    """."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        request.session.db = config.get('interface_db_name')

        """."""
        _logger.info({
            'args': args,
            'kwargs': kwargs,
            'func': func
        })
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response(
                "access_token_not_found", "missing access token in request header", 401
            )
        access_token_data = (
            request.env["api.access_token"]
            .sudo()
            .search([("token", "=", access_token)], order="id DESC", limit=1)
        )

        if (
            access_token_data.find_one_or_create_token(
                user_id=access_token_data.user_id.id
            )
            != access_token
        ):
            return invalid_response(
                "access_token", "token seems to have expired or invalid", 401
            )

        request.session.uid = access_token_data.user_id.id
        request.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)

    return wrap
