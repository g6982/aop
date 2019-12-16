# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
_logger = logging.getLogger(__name__)


class ReturnHandoverWizard(models.TransientModel):
    _name = 'return.handover.wizard'

    write_batch_id = fields.Many2one('write.off.batch.number', 'Batch')
    select_handover_ids = fields.Many2many('handover.vin', 'all_handover_ids', string='Area')
    return_handover_ids = fields.Many2many('handover.vin', 'return_handover_ids', string='Return ids')

    @api.model
    def default_get(self, fields_list):
        res = super(ReturnHandoverWizard, self).default_get(fields_list)
        ids = self._context.get('select_handover_ids', [])
        write_batch_id = self._context.get('write_off_batch_id', [])
        res['select_handover_ids'] = [(6, 0, ids)]
        res['write_batch_id'] = write_batch_id
        return res

    def return_handover(self):
        if not self.return_handover_ids:
            raise ValueError('You must select at least one record.')

        self.return_handover_ids.write({
            'state': 'register',
            'write_off_batch_id': False,
            'verify_user_id': False,
            'verify_datetime': False,
            'return_user_id': self.env.user.id,
            'return_datetime': fields.Datetime.now()
        })

        left_ids = set(self.select_handover_ids.ids) - set(self.return_handover_ids.ids)
        _logger.info({
            'left_ids': left_ids
        })
        if left_ids:
            self.write_batch_id.write({
                'handover_ids': [(6, 0, list(left_ids))]
            })
