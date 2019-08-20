# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import random
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FillServiceProductWizard(models.TransientModel):
    _name = 'fill.service.product.wizard'

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Batch')
    wizard_line_ids = fields.Many2many('fill.service.product.wizard.line', 'fill_service_product_id', string='Lines')

    def start_create_purchase_order(self):
        data = self._get_purchase_data()

        res = self.env['purchase.order'].sudo().create(data)
        self.stock_picking_batch_id.write({
            'picking_purchase_id': res.id
        })

    def _get_purchase_data(self):
        vendor = self.stock_picking_batch_id.partner_id.id
        res = {
            'name': str(time.time()),
            'partner_id': vendor,
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_batch_id': self.stock_picking_batch_id.id,
        }

        line_data = self._get_purchase_line_data()

        res.update({
            'order_line': line_data
        })
        return res

    def _get_purchase_line_data(self):
        res = []

        for picking in self.stock_picking_batch_id.picking_ids:

            service_product_id = self._parse_service_product_supplier(picking)

            if not service_product_id:
                picking_line = self.wizard_line_ids.filtered(lambda x: x.picking_id == picking)
                service_product_id = picking_line.service_product_id
                amount = picking_line.amount

            for line_id in picking.move_lines:
                data = {
                    'product_id': service_product_id.id,
                    'transfer_product_id': line_id.product_id.id,
                    'service_product_id': service_product_id.id if service_product_id else False,
                    'product_qty': line_id.product_uom_qty,
                    'name': line_id.name,
                    'date_planned': fields.Datetime.now(),
                    #'price_unit': line_id.service_product_id.lst_price,
                    'price_unit': amount,
                    'product_uom': service_product_id.uom_id.id
                }
                res.append((0, 0, data))
                # if not data['product_id'] in product_ids:
                #     product_ids.append(data['product_id'])
                #     res.append((0, 0, data))
        return res

    def _parse_service_product_supplier(self, picking):
        delivery_carrier_id = self.env['delivery.carrier'].search([
            ('supplier_contract_id.partner_id', '=', picking.partner_id.id),
            ('from_location_id', '=', picking.location_id.id),
            ('to_location_id', '=', picking.location_dest_id.id)
        ])

        return delivery_carrier_id[0].service_product_id if delivery_carrier_id else False


class FillServiceProductWizardLine(models.TransientModel):
    _name = 'fill.service.product.wizard.line'

    fill_service_product_id = fields.Many2one('fill.service.product.wizard')
    picking_id = fields.Many2one('stock.picking')
    from_location_id = fields.Many2one('stock.location')
    to_location_id = fields.Many2one('stock.location')

    service_product_id = fields.Many2one(
        'product.product',
        required=True,
        domain=[('sale_ok', '=', True), ('type', '=', 'service')]
    )

    amount = fields.Float('Amount', related='service_product_id.standard_price')

