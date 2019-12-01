#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import time

_logger = logging.getLogger(__name__)


class WriteBackAccountInvoiceLine(models.TransientModel):
    _name = 'write.back.account.invoice.line'

    def get_latest_contract_id(self):
        pass

    def get_latest_carrier_id(self):
        pass

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
            ('contract_version', '!=', 0)
        ], limit=1)
        return res

    def _get_latest_carrier_id(self, contract_id, order_line_id):
        contract_line_ids = contract_id.mapped('delivery_carrier_ids')

        from_location_id = self._transfer_district_to_location(order_line_id.from_location_id)
        to_location_id = self._transfer_district_to_location(order_line_id.to_location_id)

        for line_id in contract_line_ids:
            # 判断路由，来源地，目的地
            if from_location_id.id == line_id.from_location_id.id and \
                    to_location_id.id == line_id.to_location_id.id and order_line_id.route_id.id == line_id.route_id.id:
                # 判断合同条款中是否存在"转到条款",如存在,获取"转到条款"
                carrier_id = line_id if not line_id.goto_delivery_carrier_id else line_id.goto_delivery_carrier_id
                return carrier_id

    def _invoice_data(self, order, line_id=False, invoice_line_id=False):
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
            'user_id': order.user_id.id,
            'date_invoice': date_invoice,
            'reconciliation_batch_no': invoice_line_id.invoice_id.reconciliation_batch_no
        }

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

    def _get_account_invoice_line_data(self, line_id, sale_order_line_id, carrier_id, contract_id):
        '''
        :param line_id: 结算清单行
        :param sale_order_line_id: 销售订单行
        :param carrier_id: 合同条款
        :param contract_id: 合同
        :return:
        '''
        sale_order_id = sale_order_line_id.order_id
        service_product_id = carrier_id.service_product_id
        account_id = self._get_account_id(service_product_id, order=sale_order_id)
        contract_price = carrier_id.fixed_price

        data = []
        old_data = {
            'name': line_id.name,
            'origin': line_id.name,
            'account_id': account_id,
            'price_unit': -line_id.price_unit,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': service_product_id.uom_id.id,
            'product_id': service_product_id.id,
            'sale_line_ids': [(6, 0, [sale_order_line_id.id])],
            'sale_order_line_id': sale_order_line_id.id,
            'contract_price': -line_id.contract_price,
            'invoice_line_tax_ids': [(6, 0, line_id.invoice_line_tax_ids.ids)],
            'analytic_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
            'account_analytic_id': sale_order_id.analytic_account_id.id or False,
            'tmp_estimate': line_id.tmp_estimate,
            'customer_aop_contract_id': contract_id.id if contract_id else False
        }
        data.append((0, 0, old_data))
        new_data = {
            'name': line_id.name,
            'origin': line_id.name,
            'account_id': account_id,
            'price_unit': line_id.price_unit,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': service_product_id.uom_id.id,
            'product_id': service_product_id.id,
            'sale_line_ids': [(6, 0, [sale_order_line_id.id])],
            'sale_order_line_id': sale_order_line_id.id,
            'contract_price': contract_price,
            'invoice_line_tax_ids': [(6, 0, line_id.invoice_line_tax_ids.ids)],
            'analytic_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
            'account_analytic_id': sale_order_id.analytic_account_id.id or False,
            'tmp_estimate': line_id.tmp_estimate,
            'customer_aop_contract_id': contract_id.id if contract_id else False
        }
        data.append((0, 0, new_data))
        return data

    def write_back(self):
        ids = self.env.context.get('active_ids')
        line_ids = self.env['account.invoice.line'].browse(ids)

        invoice_obj = self.env['account.invoice']
        create_invoice_ids = []
        for line_id in line_ids:
            sale_order_line_id = line_id.sale_order_line_id

            order = sale_order_line_id.order_id

            # 合同
            contract_id = self._get_latest_contract_id(sale_order_line_id)

            # 条款
            carrier_id = self._get_latest_carrier_id(contract_id, sale_order_line_id)

            # 如果是草稿，直接修改即可
            if line_id.state == 'draft':
                tmp = {}
                if line_id.invoice_id.type == 'out_invoice':
                    tmp.update({
                        'customer_aop_contract_id': contract_id.id
                    })
                else:
                    tmp.update({
                        'supplier_aop_contract_id': contract_id.id
                    })
                tmp.update({
                    'contract_price': carrier_id.fixed_price
                })
                line_id.write(tmp)
            else:
                # 销售订单行
                # 如果发票行的状态是完成
                # 生成一条新的记录，使用最新的合同信息，先创建负数，再创建正数的新合同数据
                invoice_data = self._invoice_data(order, line_id=sale_order_line_id, invoice_line_id=line_id)
                invoice_line_data = self._get_account_invoice_line_data(line_id, sale_order_line_id, carrier_id, contract_id)
                invoice_data.update({
                    'invoice_line_ids': invoice_line_data
                })
                res = invoice_obj.create(invoice_data)
                create_invoice_ids.append(res.id)
        if not create_invoice_ids:
            return True

        view_id = self.env.ref('account.invoice_tree_with_onboarding').id
        form_id = self.env.ref('account.invoice_form').id

        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'view_id': False,
            'views': [(view_id, 'tree'), (form_id, 'form')],
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', create_invoice_ids)],
            'limit': 80,
            'target': 'current',
        }