# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import random
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cost_currency_id = fields.Many2one('res.currency', 'Cost Currency', compute='_compute_cost_currency_id')

    #vehicle_type_id = fields.Many2one('product.vehicle.type', 'Vehicle type')

    def _compute_cost_currency_id(self):
        for template in self:
            template.cost_currency_id = self.env.user.company_id.currency_id.id


class ProductVehicleType(models.Model):
    _name = 'product.vehicle.type'
    _description = 'Product vehicle type'

    name = fields.Char('Name')

    # type = fields.Char('Type')
    # brand = fields.Char('Brand')
    # model_name = fields.Char('Model')

