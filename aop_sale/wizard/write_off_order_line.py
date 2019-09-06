# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class WriteOffLineWizard(models.TransientModel):
    _name = 'write.off.line.wizard'

    write_off_line_ids = fields.One2many('write.off.line.wizard.line', 'line_wizard_id')

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


class WriteOffLineWizardLine(models.TransientModel):
    _name = 'write.off.line.wizard.line'

    line_wizard_id = fields.Many2one('write.off.line.wizard')
    sale_order_line_id = fields.Many2one('sale.order.line')
    handover_number = fields.Char('Handover')
    file_validate = fields.Binary('file')
    file_name = fields.Char("File Name")
