# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.model
    def _get_advance_payment_method(self):
        return 'all'

    advance_payment_method = fields.Selection([
        ('delivered', 'Invoiceable lines'),
        ('all', 'Invoiceable lines (deduct down payments)'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='What do you want to invoice?', default=_get_advance_payment_method, required=True)

    reconciliation_batch_no = fields.Char('Reconciliation batch no')
    invoice_product_type = fields.Selection([
        ('main_product', 'Main product'),
        ('child_product', 'Child product')
    ], required=True, string='Invoice product type')

    invoice_state = fields.Boolean('Advance receipt')

    selected_order_lines = fields.One2many('make.invoice.sale.order.line', 'payment_inv_id', string='Order lines')

    period_id = fields.Many2one('account.period', 'Period')
    write_off_batch_number_id = fields.Many2one('write.off.batch.number', 'Write-off batch')

    @api.model
    def default_get(self, fields_list):
        res = super(SaleAdvancePaymentInv, self).default_get(fields_list)

        data = []
        ids = self._context.get('active_ids', [])
        line_ids = self.env['sale.order.line'].browse(ids)
        handover_ids = self.env['handover.vin'].browse(self._context.get('handover_ids'))
        if handover_ids:
            for line_id in handover_ids:
                data.append((0, 0, {
                    'sale_order_line_id': line_id.order_line_id.id,
                    'handover_id': line_id.id
                }))
        else:
            for line_id in line_ids:
                data.append((0, 0, {
                    'sale_order_line_id': line_id.id,
                }))
        if data:
            res['selected_order_lines'] = data

        res['period_id'] = self._context.get('period_id')
        res['write_off_batch_number_id'] = self._context.get('write_off_batch_number_id')
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

        contract_line = self._get_contract_delivery(so_line)
        contract_price = contract_line.fixed_price

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

    def _null_invoice_order_line_data(self):
        sql_delete = '''
            delete from sale_order_line_invoice_rel where invoice_line_id not in (select id from account_invoice_line)
        '''
        self.env.cr.execute(sql_delete)
        self.env.cr.commit()

    # 生成结算清单
    # 根据订单行生成
    def create_account_invoice(self, order_line_amount=False):
        self._null_invoice_order_line_data()
        if not self.selected_order_lines:
            raise UserError(_('You must select more than one record.'))

        invoice_res = []
        if self.invoice_product_type == 'main_product':
            invoice_res = self._get_main_service_product_data(order_line_amount=order_line_amount)
        elif self.invoice_product_type == 'child_product':
            invoice_res = self._get_child_service_product_data(order_line_amount=order_line_amount)
        return self._create_account_invoice(invoice_res)

    def _create_account_invoice(self, invoice_res):
        try:
            inv_obj = self.env['account.invoice']
            res = inv_obj.create(invoice_res)

            self.fetch_reconciliation_data(res)

            # if not res:
            #     raise UserError('Error!')
            view_id = self.env.ref('account.invoice_tree_with_onboarding').id
            form_id = self.env.ref('account.invoice_form').id
            # if self._context.get('period_id', False):
            if self.period_id:
                context = {
                    'default_period_id': self.period_id.id
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

            if self.write_off_batch_number_id:
                self.write_off_batch_number_id.write({
                    'invoice_line_ids': [(6, 0, res.mapped('invoice_line_ids').ids)],
                    'state': 'done'
                })

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

    def _invoice_data(self, order, line_id=False):
        date_invoice = False
        if line_id:
            date_invoice = line_id.picking_confirm_date if line_id.picking_confirm_date else fields.Date.today()
            date_invoice = date_invoice.date() if hasattr(date_invoice, 'date') else date_invoice
        else:
            date_invoice = fields.Date.today()
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
            'date_invoice': date_invoice,
            'reconciliation_batch_no': self.reconciliation_batch_no
        }

    def _get_child_service_product(self, picking_ids):
        move_ids = self.env['stock.move'].search([
            ('picking_id', 'in', picking_ids.ids)
        ])
        product_ids = [move_id.service_product_id for move_id in move_ids if move_id.service_product_id]
        return list(set(product_ids))

    # 交接单
    def _find_handover_id(self, order_line_id):
        res = self.selected_order_lines.filtered(lambda x: x.sale_order_line_id == order_line_id)
        return res[0].handover_id if res else False

    def _get_child_service_product_data(self, order_line_amount=False):
        invoice_res = []
        legal_order_line_ids = self.selected_order_lines.mapped('sale_order_line_id').filtered(lambda x: x if not x.invoice_lines else '')

        # FIXME: 采购订单生成的结算清单，为什么关联到了销售呢？
        if not legal_order_line_ids:
            legal_order_line_ids = []
            for line_id in self.selected_order_lines.mapped('sale_order_line_id'):
                if line_id.invoice_lines.filtered(lambda x: x.invoice_id.type != 'out_invoice'):
                    legal_order_line_ids.append(line_id)

        product_ids = self._get_child_service_product(legal_order_line_ids.mapped('stock_picking_ids'))

        # for sale_order_id in self.sale_order_ids:
        for sale_order_id in legal_order_line_ids:
            handover_id = self._find_handover_id(sale_order_id)

            invoice_data = self._invoice_data(sale_order_id.order_id, line_id=sale_order_id)

            # tmp_estimate = sale_order_id.delivery_carrier_id.fixed_price if self._context.get(
            #     'monthly_confirm_invoice') else 0
            tmp_estimate = sale_order_id.delivery_carrier_id.fixed_price if self.period_id else 0
            contract_line = self._get_contract_delivery(sale_order_id)

            contract_price = contract_line.fixed_price
            contract_id = contract_line.customer_contract_id

            picking_create_date, picking_done_date = self.get_picking_date(sale_order_id)

            for product_id in product_ids:
                tmp = invoice_data
                account_id = self._get_account_id(product_id)
                tmp.update({
                    'invoice_line_ids': [(0, 0, {
                        'name': str(time.time()),
                        'origin': sale_order_id.name,
                        'account_id': account_id,
                        'price_unit': order_line_amount.get(sale_order_id.id, product_id.list_price),
                        'quantity': 1,
                        'product_id': product_id.id,
                        'uom_id': product_id.uom_id.id,
                        'sale_line_ids': [(6, 0, sale_order_id.ids)],
                        'sale_order_line_id': sale_order_id[0].id,
                        'contract_price': contract_price,
                        'invoice_line_tax_ids': [(6, 0, product_id.taxes_id.ids)],
                        'analytic_tag_ids': False,
                        'account_analytic_id': False,
                        'tmp_estimate': tmp_estimate,
                        'customer_aop_contract_id': contract_id.id if contract_id else False,
                        'sale_order_line_confirm_date': picking_create_date,
                        'sale_order_line_first_picking_done_date': picking_done_date,
                        'handover_id': handover_id.id if handover_id else False
                    })],
                })
                invoice_res.append(tmp)
        return invoice_res

    # 获取订单的日期
    def get_picking_date(self, sale_order_line_id):
        picking_ids = sale_order_line_id.stock_picking_ids
        if not picking_ids:
            return False, False

        picking_ids = picking_ids.sorted(lambda x: x.id)

        return picking_ids[0].scheduled_date, picking_ids[0].date_done

    def _get_main_service_product_data(self, order_line_amount=False):
        invoice_res = []

        legal_order_line_ids = self.selected_order_lines.mapped('sale_order_line_id').filtered(lambda x: x if not x.invoice_lines else '')

        # FIXME: 采购订单生成的结算清单，为什么关联到了销售呢？
        if not legal_order_line_ids:
            legal_order_line_ids = []
            for line_id in self.selected_order_lines.mapped('sale_order_line_id'):
                if line_id.invoice_lines.filtered(lambda x: x.invoice_id.type != 'out_invoice'):
                    legal_order_line_ids.append(line_id)

        for line_id in legal_order_line_ids:
            handover_id = self._find_handover_id(line_id)
            sale_order_id = line_id.mapped('order_id')
            invoice_data = self._invoice_data(sale_order_id, line_id=line_id)
            line_data = []

            account_id = self._get_account_id(line_id.service_product_id, order=sale_order_id)

            contract_line = self._get_contract_delivery(line_id)
            contract_price = contract_line.fixed_price
            contract_id = contract_line.customer_contract_id

            picking_create_date, picking_done_date = self.get_picking_date(line_id)

            tmp_estimate = line_id.delivery_carrier_id.fixed_price if self.period_id else 0
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
                'tmp_estimate': tmp_estimate,
                'customer_aop_contract_id': contract_id.id if contract_id else False,
                'sale_order_line_confirm_date': picking_create_date,
                'sale_order_line_first_picking_done_date': picking_done_date,
                'handover_id': handover_id.id if handover_id else False
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

    # 获取位置
    def _transfer_district_to_location(self, partner_id):
        return partner_id.property_stock_customer

    # 查找最新的合同版本
    def _get_latest_contract_id(self, line_id):
        partner_id = getattr(line_id, 'order_partner_id')

        if not partner_id:
            partner_id = getattr(line_id, 'partner_id')

        res = self.env['customer.aop.contract'].search([
            ('partner_id', '=', partner_id.id),
            ('contract_version', '!=', 0),
            ('date_start', '<', line_id.create_date),
            ('date_end', '>', line_id.create_date)
        ])

        if not res:
            raise UserError('Can not find correct contract !')

        return res

    # 合同价格
    # TODO: 需要获取最新的合同,同时需要合同和版本号，需要显示在结算清单行上面
    def _get_contract_delivery(self, line_id):
        # 获取最新的合同
        latest_contract_id = self._get_latest_contract_id(line_id)
        latest_carrier_id = False

        from_location_id = self._transfer_district_to_location(line_id.from_location_id)
        to_location_id = self._transfer_district_to_location(line_id.to_location_id)

        if latest_contract_id:
            # 使用通用的方法查找条款
            latest_carrier_id = latest_contract_id.find_customer_delivery_carrier_id(
                latest_contract_id,
                from_location_id,
                to_location_id,
                line_id
            )

            # 使用最新的条款的价格
            if latest_carrier_id:
                return latest_carrier_id

        return latest_carrier_id if latest_carrier_id else line_id.delivery_carrier_id
        # return line_id.delivery_carrier_id.fixed_price

    # 生成结算清单的时候。去匹配一次对帐数据
    def fetch_reconciliation_data(self, invoice_ids):
        '''
        :param invoice_ids: 生成的结算清单
        :return:
        '''
        invoice_line_ids = invoice_ids.mapped('invoice_line_ids')
        if not invoice_line_ids:
            return True

        re_file_obj = self.env['reconciliation.file']
        handover_number = invoice_line_ids.mapped('sale_order_line_id').mapped('handover_number')
        product_ids = invoice_line_ids.mapped('sale_order_line_id').mapped('product_id')

        res = re_file_obj.search([
            ('name', 'in', handover_number),
            ('product_id', 'in', product_ids.ids)
        ])
        if res:
            res.reconciliation_account_invoice()


class InvoiceOrderLine(models.TransientModel):
    _name = 'make.invoice.sale.order.line'

    payment_inv_id = fields.Many2one('sale.advance.payment.inv')

    handover_id = fields.Many2one('handover.vin', string='Handover')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line')
    currency_id = fields.Many2one(related='sale_order_line_id.currency_id')
    price_subtotal = fields.Monetary(related='sale_order_line_id.price_subtotal',
                                     string='Subtotal',
                                     readonly=True)
    receipt_amount = fields.Float('Amount')
