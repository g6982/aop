# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MailFollower(models.Model):
    _inherit = 'mail.followers'

    # 重复创建
    @api.model_create_multi
    def create(self, vals_list):
        vals_list = self._remove_duplicate(vals_list)

        res = super(MailFollower, self).create(vals_list)
        return res

    def _remove_duplicate(self, dict_list):
        seen = set()
        new_dict_list = []
        for dict_remove in dict_list:
            t_dict = {
                'res_model': dict_remove['res_model'],
                'res_id': dict_remove['res_id'],
                'partner_id': dict_remove['partner_id']
            }
            t_tup = tuple(t_dict.items())
            if t_tup not in seen:
                seen.add(t_tup)
                new_dict_list.append(dict_remove)
        return new_dict_list
