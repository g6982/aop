# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TrainManage(models.Model):
    _name = 'train.manage'

    name = fields.Char('Name')
    from_location_id = fields.Many2one('stock.location', 'From')
    to_location_id = fields.Many2one('stock.location', 'To')

    line_ids = fields.One2many('train.manage.line', 'train_id', string='Train lines')


class TrainManageLine(models.Model):
    _name = 'train.manage.line'

    name = fields.Char('Name')
    train_id = fields.Many2one('train.manage', 'Train')

