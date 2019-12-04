# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64
import logging
from io import BytesIO

_logger = logging.getLogger(__name__)

BARCODE_TYPE = ['Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8', 'Extended39',
                'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39', 'Standard93',
                'UPCA', 'USPS_4State']


class LotQrcode(models.Model):
    _inherit = 'stock.production.lot'

    def get_options(self):
        return sorted((type_id, type_id) for type_id in BARCODE_TYPE)

    image = fields.Binary('Qr code', attachment=True, compute='_compute_qr_code_image')
    barcode = fields.Binary('Barcode', attachment=True, compute='_compute_qr_code_image')
    barcode_type = fields.Selection(get_options, 'Barcode type')

    @api.multi
    @api.depends('name', 'barcode_type')
    def _compute_qr_code_image(self):
        for line in self:
            qr_image = self.env['ir.actions.report'].barcode(barcode_type='QR', value=line.name,
                                                             width=200,
                                                             height=200,
                                                             humanreadable=1)
            line.image = base64.b64encode(qr_image)

            param_type = line.barcode_type if line.barcode_type else 'Code128'

            barcode = self.env['ir.actions.report'].barcode(barcode_type=param_type, value=line.name,
                                                            humanreadable=1)
            line.barcode = base64.b64encode(barcode)
