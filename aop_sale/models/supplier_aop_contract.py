# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SupplierAopContract(models.Model):
    _inherit = 'aop.contract'
    _name = 'supplier.aop.contract'
    _description = 'supplier aop contract'
