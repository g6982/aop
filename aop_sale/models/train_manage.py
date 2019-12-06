# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TrainManage(models.Model):
    _name = 'train.manage'

    name = fields.Char('Name')
    line_ids = fields.One2many('train.manage.line', 'train_id', string='Train lines')


class TrainManageLine(models.Model):
    _name = 'train.manage.line'

    name = fields.Char('Name')
    train_id = fields.Many2one('train.manage', 'Train')

