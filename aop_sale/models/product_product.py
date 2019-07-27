from odoo import models, fields, api
import logging
import random
import time
from odoo.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    vehicle_type_id = fields.Many2one('product.vehicle.type', 'Vehicle type')