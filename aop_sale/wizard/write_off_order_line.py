# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WriteOffLineWizard(models.TransientModel):
    _name = 'write.off.line.wizard'

    name = fields.Char('Name', required=True)
    write_off_line_ids = fields.One2many('write.off.line.wizard.line', 'line_wizard_id')

    handover_vin_ids = fields.Many2many('handover.vin', string='Handover')

    def start_write_off(self):
        data = []
        for line in self.write_off_line_ids:
            line.sale_order_line_id.write({
                'handover_number': line.handover_number,
                'file_validate': line.file_validate
            })
            data.append({
                'name': line.file_name,
                'res_model': 'sale.order',
                'res_id': line.sale_order_line_id.order_id.id,
                'datas': line.file_validate,
                'type': 'binary'
            })

        res = self.env['ir.attachment'].create(data)
        return True

    @api.model
    def default_get(self, fields):
        res = super(WriteOffLineWizard, self).default_get(fields)
        ids = self._context.get('active_ids', [])

        records = self.env['handover.vin'].browse(ids).filtered(lambda x: not x.write_off_batch_id)
        if ids:
            res['handover_vin_ids'] = [(6, 0, records.ids)]
        return res

    def batch_write_off(self):
        if not self.handover_vin_ids:
            raise UserError(_('You have not select records!'))
        if self.handover_vin_ids.filtered(lambda x: x.write_off_batch_id):
            raise UserError(_('You can not select the records that have write-off'))

        data = {
            'name': self.name,
            'handover_ids': [(6, 0, self.handover_vin_ids.ids)]
        }
        res = self.env['write.off.batch.number'].create(data)
        self.handover_vin_ids.write({
            'write_off_batch_id': res.id
        })

        view_id = self.env.ref('aop_sale.view_write_off_batch_number_tree').id
        form_id = self.env.ref('aop_sale.view_write_off_batch_number_form').id

        # 跳转到导入成功后的tree界面
        return {
            'name': _('Write-off batch'),
            'view_type': 'form',
            'view_id': False,
            'views': [(view_id, 'tree'), (form_id, 'form')],
            'res_model': 'write.off.batch.number',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res.ids)],
            'limit': 80,
            'target': 'current',
        }


class WriteOffLineWizardLine(models.TransientModel):
    _name = 'write.off.line.wizard.line'

    line_wizard_id = fields.Many2one('write.off.line.wizard')
    sale_order_line_id = fields.Many2one('sale.order.line')
    handover_number = fields.Char('Handover')
    file_validate = fields.Binary('file')
    file_name = fields.Char("File Name")
