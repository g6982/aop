# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ResUsersType(models.Model):
    _name = 'res.users.type'
    _sql_constraints = [('unique_name', 'unique(name)', 'The name must be unique')]

    name = fields.Char('Name')
