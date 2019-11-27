# -*- coding: utf-8 -*-

from odoo import fields, models, api
import time
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SendWaitingList(models.Model):
    _name = 'send.waiting.list'

    picking_ids = fields.Many2many('stock.picking', string='Picking')
    partner_id = fields.Many2one('res.partner')

