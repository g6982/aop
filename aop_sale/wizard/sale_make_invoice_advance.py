# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    reconciliation_batch_no = fields.Char('Reconciliation batch no')
    invoice_product_type = fields.Selection([
        ('main_product', 'Main product'),
        ('child_product', 'Child product')
    ], required=True, string='Invoice product type')

    invoice_state = fields.Boolean('Advance receipt')

    sale_order_ids = fields.Many2many('sale.order', string='Orders')

    selected_order_lines = fields.One2many('make.invoice.sale.order.line', 'payment_inv_id', string='Order lines')

    @api.onchange('sale_order_ids', 'invoice_state')
    def parse_sale_order_line_ids(self):
        if not self.sale_order_ids:
            self.selected_order_lines = False
            return False

        line_ids = self.sale_order_ids.mapped('order_line')

        # if not self.invoice_state:
        #     line_ids = self.sale_order_ids.mapped('order_line').filtered(
        #         lambda x: x.handover_number is not False or x.state == 'sale')
        # else:
        #     line_ids = self.sale_order_ids.mapped('order_line').filtered(
        #         lambda x: x.handover_number is False or x.state != 'sale')

        self.selected_order_lines = False

        data = []
        for line_id in line_ids:
            data.append((0, 0, {
                    'sale_order_line_id': line_id.id
                }))
        self.selected_order_lines = data

    @api.model
    def default_get(self, fields_list):
        if self._context.get('active_model', False) == 'sale.order.line':
            return []
        else:
            res = super(SaleAdvancePaymentInv, self).default_get(fields_list)
            ids = self._context.get('active_ids', [])
            res['sale_order_ids'] = [(6, 0, ids)]
            return res

    @api.multi
    def create_invoices(self):
        if self._context.get('active_model', False) == 'sale.order.line':
            sale_order_lines = self.env['sale.order.line'].browse(self._context.get('active_ids', []))
            sale_orders = sale_order_lines.order_id if sale_order_lines else []
        else:
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_(
                        'The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_(
                        "The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'analytic_tag_ids': analytic_tag_ids,
                    'tax_id': [(6, 0, tax_ids)],
                    'is_downpayment': True,
                })
                del context
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        inv_obj = self.env['account.invoice']
        ir_property_obj = self.env['ir.property']

        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id or self.product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        if not account_id:
            raise UserError(
                _(
                    'There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                (self.product_id.name,))

        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))
        context = {'lang': order.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            amount = order.amount_untaxed * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount,)
        else:
            amount = self.amount
            name = _('Down Payment')
        del context
        taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
        if order.fiscal_position_id and taxes:
            tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
        else:
            tax_ids = taxes.ids

        contract_price = self._get_contract_price(so_line)

        invoice = inv_obj.create({
            'name': order.client_order_ref or order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'origin': order.name,
                'account_id': account_id,
                'price_unit': amount,
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': self.product_id.uom_id.id,
                'product_id': self.product_id.id,
                'sale_line_ids': [(6, 0, [so_line.id])],
                'sale_order_line_id': so_line.id,
                'contract_price': contract_price,
                'invoice_line_tax_ids': [(6, 0, tax_ids)],
                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                'account_analytic_id': order.analytic_account_id.id or False,
            })],
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_term_id': order.payment_term_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'team_id': order.team_id.id,
            'user_id': order.user_id.id,
            'comment': order.note,
            'reconciliation_batch_no': self.reconciliation_batch_no
        })
        invoice.compute_taxes()
        invoice.message_post_with_view('mail.message_origin_link',
                                       values={'self': invoice, 'origin': order},
                                       subtype_id=self.env.ref('mail.mt_note').id)
        return invoice

    # 生成结算清单
    # 根据订单行生成
    def create_account_invoice(self, order_line_amount=False):
        if not self.selected_order_lines:
            raise UserError('You must select more than one record.')

        invoice_res = []
        if self.invoice_product_type == 'main_product':
            invoice_res = self._get_main_service_product_data(order_line_amount)
        elif self.invoice_product_type == 'child_product':
            invoice_res = self._get_child_service_product_data(order_line_amount)
        return self._create_account_invoice(invoice_res)

    def _create_account_invoice(self, invoice_res):
        try:
            inv_obj = self.env['account.invoice']
            res = inv_obj.create(invoice_res)
            # if not res:
            #     raise UserError('Error!')
            view_id = self.env.ref('account.invoice_tree_with_onboarding').id
            form_id = self.env.ref('account.invoice_form').id
            if self._context.get('period_id', False):
                context = {
                    'default_period_id': self._context.get('period_id')
                }
                return {
                    'name': _('Monthly'),
                    'view_type': 'form',
                    "view_mode": 'form',
                    'res_model': 'month.close.wizard',
                    'type': 'ir.actions.act_window',
                    'context': context,
                    'target': 'new',
                }

            return {
                'name': _('Invoice'),
                'view_type': 'form',
                'view_id': False,
                'views': [(view_id, 'tree'), (form_id, 'form')],
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', res.ids)],
                'limit': 80,
                'target': 'current',
            }
        except Exception as e:
            import traceback
            raise UserError(traceback.format_exc())

    def _invoice_data(self, order):
        return {
            'name': order.client_order_ref or order.name + '/' + str(time.time()),
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_term_id': order.payment_term_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            # 'team_id': order.team_id.id,
            'user_id': order.user_id.id,
            # 'comment': order.note,
            'date_invoice': fields.Date.today(),
            'reconciliation_batch_no': self.reconciliation_batch_no
        }

    def _get_child_service_product(self, picking_ids):
        move_ids = self.env['stock.move'].search([
            ('picking_id', 'in', picking_ids.ids)
        ])
        product_ids = [move_id.service_product_id for move_id in move_ids if move_id.service_product_id]
        return list(set(product_ids))

    def _get_child_service_product_data(self, order_line_amount=False):
        invoice_res = []
        legal_order_line_ids = self.selected_order_lines.mapped('sale_order_line_id').filtered(lambda x: x if not x.invoice_lines else '')

        product_ids = self._get_child_service_product(legal_order_line_ids.mapped('stock_picking_ids'))

        _logger.info({
            'product_ids': product_ids
        })
        # for sale_id in self.sale_order_ids:
        for sale_id in legal_order_line_ids:
            invoice_data = self._invoice_data(sale_id.order_id)

            tmp_estimate = sale_id.delivery_carrier_id.fixed_price if self._context.get(
                'monthly_confirm_invoice') else 0
            contract_price = self._get_contract_price(sale_id)
            for product_id in product_ids:
                tmp = invoice_data
                account_id = self._get_account_id(product_id)
                tmp.update({
                    'invoice_line_ids': [(0, 0, {
                        'name': str(time.time()),
                        'origin': sale_id.name,
                        'account_id': account_id,
                        'price_unit': order_line_amount.get(sale_id.id, product_id.list_price),
                        'quantity': 1,
                        'product_id': product_id.id,
                        'uom_id': product_id.uom_id.id,
                        'sale_line_ids': [(6, 0, sale_id.ids)],
                        'sale_order_line_id': sale_id[0].id,
                        'contract_price': contract_price,
                        'invoice_line_tax_ids': [(6, 0, product_id.taxes_id.ids)],
                        'analytic_tag_ids': False,
                        'account_analytic_id': False,
                        'tmp_estimate': tmp_estimate
                        # 'customer_price': contract_price
                    })],
                })
                invoice_res.append(tmp)
        return invoice_res

    def _get_main_service_product_data(self, order_line_amount=False):
        invoice_res = []

        legal_order_line_ids = self.selected_order_lines.mapped('sale_order_line_id').filtered(lambda x: x if not x.invoice_lines else '')

        for line_id in legal_order_line_ids:
            sale_order_id = line_id.mapped('order_id')
            invoice_data = self._invoice_data(sale_order_id)
            line_data = []

            account_id = self._get_account_id(line_id.service_product_id, order=sale_order_id)
            contract_price = self._get_contract_price(line_id)

            tmp_estimate = line_id.delivery_carrier_id.fixed_price if self._context.get('monthly_confirm_invoice') else 0
            line_data.append((0, 0, {
                'name': str(time.time()),
                'origin': sale_order_id.name,
                'account_id': account_id,
                'price_unit': order_line_amount.get(line_id.id, contract_price),
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': line_id.service_product_id.uom_id.id,
                'product_id': line_id.service_product_id.id,
                'sale_line_ids': [(6, 0, [line_id.id])],
                'sale_order_line_id': line_id.id,
                'contract_price': contract_price,
                'invoice_line_tax_ids': [(6, 0, line_id.tax_id.ids)],
                'analytic_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
                'account_analytic_id': sale_order_id.analytic_account_id.id or False,
                'tmp_estimate': tmp_estimate
                # 'customer_price': contract_price
            }))

            invoice_data.update({
                'invoice_line_ids': line_data
            })
            invoice_res.append(invoice_data)
        return invoice_res

    def _get_account_id(self, service_product_id, order=False):
        ir_property_obj = self.env['ir.property']
        account_id = False
        if service_product_id.id:
            account_id = service_product_id.property_account_income_id.id or \
                         service_product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc and order else False
        if not account_id:
            raise UserError(
                _(
                    'There is no income account defined for this product: "%s". '
                    'You may have to install a chart of account from Accounting app, settings menu.') %
                (service_product_id.name,))
        return account_id

    # 合同价格
    def _get_contract_price(self, line_id):
        return line_id.delivery_carrier_id.fixed_price


class InvoiceOrderLine(models.TransientModel):
    _name = 'make.invoice.sale.order.line'

    payment_inv_id = fields.Many2one('sale.advance.payment.inv')

    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line')
    currency_id = fields.Many2one(related='sale_order_line_id.currency_id')
    price_subtotal = fields.Monetary(related='sale_order_line_id.price_subtotal',
                                     string='Subtotal',
                                     readonly=True)
    receipt_amount = fields.Float('Amount')
