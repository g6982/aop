#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import time

_logger = logging.getLogger(__name__)


class WriteBackAccountInvoiceLine(models.TransientModel):
    _name = 'write.back.account.invoice.line'

    # 获取位置
    def _transfer_district_to_location(self, partner_id):
        return partner_id.property_stock_customer

    # 查找最新的合同版本
    def _get_latest_contract_id(self, invoice_line_id):
        partner_id = invoice_line_id.partner_id

        if invoice_line_id.invoice_id.type == 'out_invoice':
            contract_obj = self.env['customer.aop.contract']
        elif invoice_line_id.invoice_id.type == 'in_invoice':
            contract_obj = self.env['supplier.aop.contract']

        now_date = fields.Datetime.now()
        res = contract_obj.sudo().search([
            ('partner_id', '=', partner_id.id),
            ('contract_version', '!=', 0),
            ('date_start', '<', now_date),
            ('date_end', '>', now_date)
        ])
        return res

    # 客户合同条款
    def _get_customer_carrier_id(self, contract_ids, order_line_id):

        from_location_id = self._transfer_district_to_location(order_line_id.from_location_id)
        to_location_id = self._transfer_district_to_location(order_line_id.to_location_id)

        # 使用通用的方法查找条款
        latest_carrier_id = contract_ids.find_customer_delivery_carrier_id(
            contract_ids,
            from_location_id,
            to_location_id,
            order_line_id
        )

        if not latest_carrier_id:
            raise UserError('Can not find correct carrier delivery')

        return latest_carrier_id

    def _invoice_data(self, invoice_line_id=False):
        # 使用当前日期
        date_invoice = fields.Date.today()

        invoice_id_data = invoice_line_id.invoice_id.copy_data()
        invoice_id_data = invoice_id_data[0]
        invoice_id_data.update({
            'date_invoice': date_invoice
        })

        # 复制部分的数据
        return {
            'name': invoice_id_data.get('name'),
            'origin': invoice_id_data.get('origin'),
            'type': invoice_id_data.get('type'),
            'reference': invoice_id_data.get('reference'),
            'account_id': invoice_id_data.get('account_id'),
            'partner_id': invoice_id_data.get('partner_id'),
            'partner_shipping_id': invoice_id_data.get('partner_shipping_id'),
            'currency_id': invoice_id_data.get('currency_id'),
            'payment_term_id': invoice_id_data.get('payment_term_id'),
            'fiscal_position_id': invoice_id_data.get('fiscal_position_id'),
            'user_id': invoice_id_data.get('user_id'),
            'date_invoice': date_invoice,
            'reconciliation_batch_no': invoice_id_data.get('reconciliation_batch_no')
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

    def _get_account_invoice_line_customer_data(self, line_id, sale_order_line_id, carrier_id, contract_id):
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
            # 'tmp_estimate': line_id.tmp_estimate,
            'tmp_estimate': 0.0,
            'customer_aop_contract_id': contract_id.id if contract_id else False,
            'supplier_aop_contract_id': False
        }
        data.append((0, 0, old_data))
        new_data = {
            'name': line_id.name,
            'origin': line_id.name,
            'account_id': account_id,
            'price_unit': contract_price,
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
            # 'tmp_estimate': line_id.tmp_estimate,
            'tmp_estimate': 0.0,
            'customer_aop_contract_id': contract_id.id if contract_id else False,
            'supplier_aop_contract_id': False
        }
        data.append((0, 0, new_data))
        return data

    def _get_account_invoice_line_supplier_data(self, line_id, carrier_id, contract_id):
        '''
        :param line_id: 结算清单行
        :param carrier_id: 合同条款
        :param contract_id: 合同
        :return:
        '''

        data = []
        invoice_line_data = line_id.copy_data()
        invoice_line_data = invoice_line_data[0]

        contract_price = carrier_id.fixed_price

        old_data = invoice_line_data
        new_data = invoice_line_data
        old_data.update({
            'price_unit': -line_id.price_unit,
            'contract_price': -line_id.contract_price,
            'supplier_aop_contract_id': contract_id.id if contract_id else False,
            'customer_aop_contract_id': False
        })

        data.append((0, 0, old_data))

        new_data.update({
            'price_unit': contract_price,
            'contract_price': contract_price,
            'supplier_aop_contract_id': contract_id.id if contract_id else False,
            'customer_aop_contract_id': False
        })
        data.append((0, 0, new_data))
        return data

    @api.multi
    def write_back_customer_invoice(self, invoice_line_id):
        invoice_data = ''
        sale_order_line_id = invoice_line_id.sale_order_line_id

        # 合同
        contract_ids = self._get_latest_contract_id(invoice_line_id)

        # 条款
        carrier_id = self._get_customer_carrier_id(contract_ids, sale_order_line_id)
        contract_id = carrier_id.customer_contract_id

        # 如果是草稿，直接修改即可
        if invoice_line_id.state == 'draft':
            tmp = {
                'customer_aop_contract_id': contract_id.id,
                'contract_price': carrier_id.fixed_price,
                'price_unit': carrier_id.fixed_price
            }
            invoice_line_id.write(tmp)
        else:
            # 销售订单行
            # 如果发票行的状态是完成
            # 生成一条新的记录，使用最新的合同信息，先创建负数，再创建正数的新合同数据
            invoice_data = self._invoice_data(invoice_line_id=invoice_line_id)
            invoice_line_data = self._get_account_invoice_line_customer_data(
                invoice_line_id,
                sale_order_line_id,
                carrier_id,
                contract_id
            )
            invoice_data.update({
                'invoice_line_ids': invoice_line_data
            })
        return invoice_data if invoice_data else False

    @api.multi
    def write_back_supplier_invoice(self, invoice_line_id):
        invoice_data = ''
        purchase_line_id = invoice_line_id.purchase_line_id

        # 合同
        contract_ids = self._get_latest_contract_id(invoice_line_id)
        # 条款
        carrier_id = contract_ids.find_supplier_delivery_carrier_id(contract_ids, purchase_line_id)

        contract_id = carrier_id.supplier_contract_id
        # _logger.info({
        #     'contract_id': contract_id,
        #     'carrier_id': carrier_id,
        #     'price': carrier_id.fixed_price
        # })
        # 如果是草稿，直接修改即可
        if invoice_line_id.state == 'draft':
            invoice_line_id.sudo().write({
                'supplier_aop_contract_id': contract_id.id,
                'contract_price': carrier_id.product_standard_price
            })
        else:
            # 销售订单行
            # 如果发票行的状态是完成
            # 生成一条新的记录，使用最新的合同信息，先创建负数，再创建正数的新合同数据
            invoice_data = self._invoice_data(invoice_line_id=invoice_line_id)
            invoice_line_data = self._get_account_invoice_line_supplier_data(
                invoice_line_id,
                carrier_id,
                contract_id
            )
            invoice_data.update({
                'invoice_line_ids': invoice_line_data
            })
        return invoice_data if invoice_data else []

    def write_back_insurance_invoice(self, invoice_line_id):
        purchase_line_id = invoice_line_id.purchase_line_id
        carrier_id = self.env['insurance.aop.contract'].find_insurance_delivery_carrier_id(purchase_line_id)

        # 有可能是保险合同!!!
        if hasattr(carrier_id, 'contract_id'):
            contract_id = carrier_id.contract_id
            if invoice_line_id.state == 'draft':
                invoice_line_id.sudo().write({
                    'insurance_aop_contract_id': contract_id.id,
                    'contract_price': carrier_id.fixed_price
                })
            # 如果已经完成了，需要生成新的
            # else:
            #     # 销售订单行
            #     # 如果发票行的状态是完成
            #     # 生成一条新的记录，使用最新的合同信息，先创建负数，再创建正数的新合同数据
            #     invoice_data = self._invoice_data(invoice_line_id=invoice_line_id)
            #     invoice_line_data = self._get_account_invoice_line_supplier_data(
            #         invoice_line_id,
            #         carrier_id,
            #         contract_id
            #     )
            #     invoice_data.update({
            #         'invoice_line_ids': invoice_line_data
            #     })
            # return False

    def write_back(self):
        ids = self.env.context.get('active_ids')
        line_ids = self.env['account.invoice.line'].browse(ids)

        # 确认价大于0的才能红冲
        line_ids = line_ids.filtered(lambda x: x.price_unit > 0)

        invoice_obj = self.env['account.invoice']
        create_invoice_ids = []
        create_invoice_values = []

        # 结算清单行
        for line_id in line_ids:

            # 回款结算清单
            if line_id.invoice_id.type == 'out_invoice':
                tmp = self.write_back_customer_invoice(line_id)
            elif line_id.invoice_id.type == 'in_invoice':
                if line_id.purchase_line_id.batch_stock_picking_id:
                    tmp = self.write_back_supplier_invoice(line_id)
                else:
                    # 保险
                    self.write_back_insurance_invoice(line_id)

            if tmp:
                create_invoice_values.append(tmp)

        if create_invoice_values:
            create_invoice_ids = invoice_obj.create(create_invoice_values).ids

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
