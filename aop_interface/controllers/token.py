# Part of odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

import werkzeug.wrappers

from odoo import http
from .tools import validate_token, valid_response, invalid_response, extract_arguments
from odoo.http import request

_logger = logging.getLogger(__name__)

expires_in = "aop_interface.access_token_expires_in"


class AccessToken(http.Controller):
    """."""

    def __init__(self):

        self._token = request.env["api.access_token"]
        self._expires_in = request.env.ref(expires_in).sudo().value

    @http.route("/api/auth/token", methods=["POST"], type="json", auth="none", csrf=False)
    def token(self, **post):
        """The token URL to be used for getting the access_token:

        Args:
            **post must contain login and password.
        Returns:

            returns https response code 404 if failed error message in the body in json format
            and status code 202 if successful with the access_token.
        Example:

            import requests
            import json

            headers = {'Content-Type': 'application/json', 'charset': 'utf-8'}

            data = {
                'params': {
                    'login': 'admin',
                    'password': 'admin',
                    'db': 'galago.ng'
                }

            }
            base_url = 'http://127.0.0.1:8069'
            req = requests.post(
                '{}/api/auth/token'.format(base_url), data=json.dumps(data), headers=headers)
            content = json.loads(req.content.decode('utf-8'))
            result = json.loads(content.get('result'))
            headers.update({
                'access-token': result.get('access_token')
            })

        """
        _token = request.env["api.access_token"]
        params = ["db", "login", "password"]
        params = {key: post.get(key) for key in params if post.get(key)}
        db, username, password = (
            params.get("db"),
            post.get("login"),
            post.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        _logger.info({
            '_credentials_includes_in_body': _credentials_includes_in_body
        })
        if not _credentials_includes_in_body:
            # The request post body is empty the credetials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error",
                    "either of the following are missing [db, username,password]",
                    403,
                )
        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response("wrong database name", error, info)

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(401, error, info)

        # Generate tokens
        access_token = _token.find_one_or_create_token(user_id=uid, create=True)

        # Successful response:
        return json.dumps(
                {
                    "uid": uid,
                    "user_context": request.session.get_context() if uid else {},
                    "company_id": request.env.user.company_id.id if uid else None,
                    "access_token": access_token,
                    "expires_in": self._expires_in,
                }
            )
