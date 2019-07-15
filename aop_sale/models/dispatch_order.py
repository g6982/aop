# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DispatchOrder(models.Model):
    _inherit = 'purchase.order'

    dispatch_order = fields.Boolean('Dispatch', compute='_compute_is_dispatch', store=True)

    @api.depends('partner_id')
    def _compute_is_dispatch(self):
        for order in self:
            if self._context.get('dispatch_order', False):
                order.dispatch_order = True
            else:
                order.dispatch_order = False

    @api.multi
    def action_view_invoice(self):
        if self.dispatch_order:
            return self.purchase_to_sale_invoice()
        else:
            return super(DispatchOrder, self).action_view_invoice()

    def purchase_to_sale_invoice(self):
        view = self.env.ref('account.invoice_form')
        if self.invoice_ids:
            res = self.invoice_ids[0]
        else:
            invoice_obj = self.env['account.invoice']
            invoice_data = self.prepare_invoice_data()
            line_data = self.prepare_order_line()
            # override the context to get rid of the default filtering
            invoice_data.update({
                'invoice_line_ids': line_data
            })
            res = invoice_obj.create(invoice_data)

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(view.id, 'form')],
            'res_id': res.id,
            'target': 'current'
        }

    def prepare_invoice_data(self):
        data = {
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'company_id': self.company_id.id if self.company_id else False,
            'type': 'out_invoice',
            'purchase_id': self.id,
            'origin': self.name,
            'currency_id': self.currency_id.id,
            'account_id': self.partner_id.property_account_receivable_id.id
        }
        return data

    def prepare_order_line(self):
        ir_property_obj = self.env['ir.property']
        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id or self.product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = self.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        data = []
        for line_id in self.order_line:
            data.append((0, 0, {
                'product_id': line_id.product_id.id,
                'name': line_id.product_id.name,
                'quantity': line_id.product_qty,
                'uom_id': line_id.product_id.uom_id.id,
                'price_unit': line_id.price_unit,
                'invoice_line_tax_ids': [(6, 0, line_id.taxes_id.ids)],
                'purchase_line_id': line_id.id,
                'account_id': account_id
            }))
        return data

