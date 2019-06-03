# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import traceback
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_take_care_id = fields.Many2one('res.partner',
                                          string='Take Car Address',
                                          readonly=True,
                                          required=False,
                                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
                                                  'sale': [('readonly', False)]},
                                          help="Take car address for current sales order.")

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('carrier', 'Quotation Confirm'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')



    @api.multi
    def action_quotation_confirm(self):
        self.ensure_one()
        return self.filtered(lambda o: o.state in ('draft', 'sent')).write({'state': 'carrier'})

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        if not self.partner_id:
            self.update({
                'partner_take_care_id': False,
            })
            return

        addr = self.partner_id.address_get(['take'])
        values = {
            'partner_take_care_id': addr['take'],
        }

        self.update(values)

    def _create_delivery_line(self, carrier, price_unit):
        if self.carrier_id.aop_route_ids if self.carrier_id else False:
            delivery_price_value = self._parse_delivery_price(carrier, price_unit)
            self.order_line.write(delivery_price_value)
        else:
            res = super(SaleOrder, self)._create_delivery_line(carrier, price_unit)

            return res

    def _parse_delivery_price(self, carrier, price_unit):
        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, carrier.product_id, self.partner_id).ids

        route_id = self.carrier_id.aop_route_ids.route_id.id
        # Create the sales order line
        values = {
            'product_uom_qty': 1,
            'service_product_id': carrier.product_id.id,
            'price_unit': price_unit,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
            # 'route_id': route_id
        }

        return values

    @api.multi
    def _remove_delivery_line(self):
        if self.carrier_id.aop_route_ids if self.carrier_id else False:
            pass
        else:
            return super(SaleOrder, self)._remove_delivery_line()

    #@api.onchange('partner_id')
    #def _domain_delivery_carrier(self):
    #    if self.partner_id:
    #        return {'domain': {'carrier_id': [('partner_id', '=', self.partner_id.id)]}}
    #    else:
    #        return {
    #            'domain': []
    #        }

    def open_vin_picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        # VIN 码过滤
        # pickings = self.mapped('picking_ids')
        pickings = self._get_product_production_lot()

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def _get_product_production_lot(self):
        data = []
        for line_id in self.order_line:
            move_line_ids = self.env['stock.move.line'].search([
                ('lot_id', '=', line_id.vin.id),
                ('move_id.product_id', '=', line_id.product_id.id)
            ])
            for move_line in move_line_ids:
                data.append(move_line.move_id.picking_id.id) if move_line else False

        return self.env['stock.picking'].browse(data)

    @api.multi
    def _action_confirm(self):
        return super(SaleOrder, self.with_context({'do_not_merge': True}))._action_confirm()
