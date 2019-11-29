# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ResUsersType(models.Model):
    _name = 'res.users.type'

    name = fields.Char('Name')
