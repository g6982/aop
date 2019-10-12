# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class DynamicView(models.TransientModel):
    _name = 'web_views_list_dynamic.view'

    #
    def get_views(self):
        import time
        _logger.info({
            'time': time.time()
        })
        return {
            'msg': 'success'
        }