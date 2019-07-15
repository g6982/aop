# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DispatchOrder(models.Model):
    _inherit = 'purchase.order'
    _name = 'dispatch.order.stock'
    _description = 'Dispatch order for stock'

    order_line = fields.One2many('dispatch.order.stock.line', 'order_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('dispatch.order.stock') or '/'
        return super(DispatchOrder, self).create(vals)

    @api.multi
    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'dispatch.order.stock',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_template(template.lang, ctx['default_model'], ctx['default_res_id'])

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'purchase':
            return 'aop_sale.mt_rfq_approved'
        elif 'state' in init_values and self.state == 'to approve':
            return 'aop_sale.mt_rfq_confirmed'
        elif 'state' in init_values and self.state == 'done':
            return 'aop_sale.mt_rfq_done'
        return super(DispatchOrder, self)._track_subtype(init_values)

    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        inv_obj = self.env['account.invoice']
        result = self._prepare_invoice_data()
        data = self.prepare_invoice_line_context()
        result.update({
            'invoice_line_ids': data
        })
        inv_id = inv_obj.create(result)
        self.invoice_ids = [(6, 0, [x for x in self.invoice_ids.ids + inv_id.ids])]
        print(result)
        return result

    def _prepare_invoice_data(self):
        data = {
            'partner_id': self.partner_id.id
        }
        return data

    def prepare_invoice_line_context(self):
        ir_property_obj = self.env['ir.property']
        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id or \
                         self.product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = self.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        if not account_id:
            raise UserError(
                _(
                    'There is no income account defined for this product: "%s". '
                    'You may have to install a chart of account from Accounting app, settings menu.') %
                (self.product_id.name,))

        taxes = self.product_id.taxes_id.filtered(lambda r: not self.company_id or r.company_id == self.company_id)
        if self.fiscal_position_id and taxes:
            tax_ids = self.fiscal_position_id.map_tax(taxes, self.product_id, self.partner_shipping_id).ids
        else:
            tax_ids = taxes.ids

        data = []
        for line_id in self.order_line:
            data.append((0, 0, {
                'name': line_id.name,
                'origin': self.name,
                'account_id': account_id,
                'price_unit': line_id.price_total,
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': self.product_id.uom_id.id,
                'product_id': self.product_id.id,
                'dispatch_line_id': line_id.id,
                'invoice_line_tax_ids': [(6, 0, tax_ids)],
                # 'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                'account_analytic_id': False,
            })
                        )
        return data


class DispatchOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    _name = 'dispatch.order.stock.line'
    _description = 'Dispatch order line for stock'

    order_id = fields.Many2one('dispatch.order.stock', string='Order Reference', index=True, required=True,
                               ondelete='cascade')


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    dispatch_line_id = fields.Many2one('dispatch.order.stock.line', 'Dispatch Order Line', ondelete='set null',
                                       index=True,
                                       readonly=True)
