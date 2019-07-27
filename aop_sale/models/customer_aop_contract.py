# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CustomerAopContract(models.Model):
    _inherit = 'aop.contract'
    _name = 'customer.aop.contract'
    _description = 'customer aop contract'
