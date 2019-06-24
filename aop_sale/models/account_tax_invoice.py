# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)


class AccountTaxInvoice(models.Model):
    _name = 'account.tax.invoice'

    name = fields.Char('Name')
