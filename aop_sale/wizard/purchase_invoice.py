# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
_logger = logging.getLogger(__name__)


class PurchaseOrderInvoiceWizard(models.TransientModel):
    _name = 'purchase.order.invoice.wizard'

    purchase_order_ids = fields.Many2many('purchase.order')
    reconciliation_batch_no = fields.Char('Reconciliation batch no', required=True)

    @api.model
    def default_get(self, fields_list):

        if self._context.get('active_model', False) == 'purchase.order' or not self._context.get('active_ids', False):
            return []
        else:
            res = super(PurchaseOrderInvoiceWizard, self).default_get(fields_list)
            ids = self._context.get('active_ids', [])

            purchase_partner_ids = self.env['purchase.order'].browse(ids).mapped('partner_id')
            code = self.env['ir.sequence'].next_by_code('seq_invoice_supplier_code')
            batch_no = self.part_partner_id_code(purchase_partner_ids, code)

            res['purchase_order_ids'] = [(6, 0, ids)]
            res['reconciliation_batch_no'] = batch_no
            return res

    def judge_purchase_not_draft(self):
        for line_id in self.purchase_order_ids:
            if line_id.state in ('draft', 'sent', 'cancel'):
                raise UserError('The order can\'t be draft')

    def generate_account_invoice(self):
        self.judge_purchase_not_draft()

        purchase_ids = self.purchase_order_ids
        data = []
        reconciliation_batch_no = self.reconciliation_batch_no
        for line in purchase_ids:
            invoice_data = {
                'partner_id': line.partner_id.id,
                'partner_shipping_id': line.partner_id.id,
                'company_id': line.company_id.id if line.company_id else False,
                'type': 'in_invoice',
                'purchase_id': line.id,
                'origin': line.name,
                'currency_id': line.currency_id.id,
                'account_id': line.partner_id.property_account_receivable_id.id,
                'date_invoice': fields.Date.today(),
                'reconciliation_batch_no': reconciliation_batch_no,
            }
            line_data = []
            for line_id in line.order_line:
                # 如果已经生成了。不需要继续生成, 如果金额为0，也不需要生成
                if line_id.invoice_lines or line_id.price_unit == 0:
                    continue
                tmp = self._prepare_invoice_line_from_po_line(line_id)
                line_data.append((0, 0, tmp))

            if not line_data:
                continue
            invoice_data.update({
                'invoice_line_ids': line_data
            })
            data.append(invoice_data)

        if data:
            invoice_obj = self.env['account.invoice']
            res = invoice_obj.create(data)
            self._create_purchase_invoice_no(res)

    # 供应商账单，创建一张表
    def _create_purchase_invoice_no(self, invoice_ids):
        purchase_invoice_batch_obj = self.env['purchase.invoice.batch.no']
        invoice_batch_no = invoice_ids.read_group(
            domain=[('id', 'in', invoice_ids.ids)],
            fields=['reconciliation_batch_no'],
            groupby='reconciliation_batch_no'
        )
        data = []
        for batch_no in invoice_batch_no:
            purchase_invoice_ids = invoice_ids.filtered(
                lambda x: x.reconciliation_batch_no == batch_no.get('reconciliation_batch_no', False)
            )
            if not purchase_invoice_ids:
                continue
            invoice_batch_id = purchase_invoice_batch_obj.search([
                ('name', '=', batch_no.get('reconciliation_batch_no', False)),
                ('partner_id', '=', purchase_invoice_ids[0].partner_id.id)
            ])
            if invoice_batch_id:
                # update
                invoice_batch_id.update({
                    'invoice_line_ids': [(4, line_id.id) for line_id in
                                         purchase_invoice_ids.mapped('invoice_line_ids')]
                })
            else:
                data.append({
                    'name': batch_no.get('reconciliation_batch_no'),
                    'partner_id': purchase_invoice_ids[0].partner_id.id,
                    'invoice_line_ids': [(6, 0, purchase_invoice_ids.mapped('invoice_line_ids').ids)]
                })
        if data:
            purchase_invoice_batch_obj.create(data)

    def _prepare_invoice_line_from_po_line(self, line):
        if line.product_id.purchase_method == 'purchase':
            qty = line.product_qty - line.qty_invoiced
        else:
            qty = line.qty_received - line.qty_invoiced
        if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
            qty = 0.0
        taxes = line.taxes_id
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id,
                                                                        line.order_id.partner_id)
        invoice_line = self.env['account.invoice.line']
        # date = self.date or self.date_invoice
        date = False
        journal_domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', line.order_id.company_id.id),
            ('currency_id', '=', line.order_id.partner_id.property_purchase_currency_id.id),
        ]
        journal_id = self.env['account.journal'].search(journal_domain, limit=1)

        # contract_price = self._get_contract_price(line)

        contract_ids = self._get_supplier_aop_contract(line)
        carrier_id = self._get_contract_price(contract_ids, line)
        contract_price = carrier_id.product_standard_price if carrier_id else 0
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name + ': ' + line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context(
                {'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': contract_price,
            'quantity': 1,
            'discount': 0.0,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids,
            'sale_order_line_id': line.sale_line_id.id if line.sale_line_id else False,
            'sale_line_ids': [(6, 0, line.sale_line_id.ids)] if line.sale_line_id else False,
            'location_id': line.batch_stock_picking_id.location_id.id,
            'location_dest_id': line.batch_stock_picking_id.location_dest_id.id,
            'contract_price': contract_price,
            'supplier_aop_contract_id': carrier_id.supplier_contract_id.id
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id,
                                                        self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

    def part_partner_id_code(self, partner_id, code):
        partner_id = partner_id[0] if partner_id else False
        # code is null? impossible!
        if not code:
            return False
        code_part = code.split('/')

        code_part.insert(4, str(partner_id.id))

        code = '/'.join(x for x in code_part)

        return code

    def _get_contract_price(self, purchase_line_id):
        picking_id = purchase_line_id.batch_stock_picking_id
        if not picking_id:
            return 0
        res = self.env['delivery.carrier'].search([
            ('from_location_id', '=', picking_id.location_id.id),
            ('to_location_id', '=', picking_id.location_dest_id.id),
            ('supplier_contract_id.partner_id', '=', purchase_line_id.order_id.partner_id.id),
            ('service_product_id', '=', purchase_line_id.product_id.id)
        ])
        return res[0].product_standard_price if res else 0

    def _get_delivery_carrier_id(self, contract_ids, purchase_line_id):
        latest_carrier_id = False
        for contract_id in contract_ids:
            if latest_carrier_id:
                continue
            picking_id = purchase_line_id.batch_stock_picking_id
            if not picking_id:
                return 0
            res = self.env['delivery.carrier'].search([
                ('from_location_id', '=', picking_id.location_id.id),
                ('to_location_id', '=', picking_id.location_dest_id.id),
                ('supplier_contract_id', '=', contract_id.id),
                ('service_product_id', '=', purchase_line_id.product_id.id)
            ])
            latest_carrier_id = res[0]

        if not latest_carrier_id:
            raise UserError('Can not find correct supplier contract !')
        return latest_carrier_id

    def _get_supplier_aop_contract(self, purchase_line_id):
        '''
        获取供应商合同
        :param purchase_line_id: 采购订单行
        :return: 获取到的供应商合同
        '''
        now_date = fields.Datetime.now()
        res = self.env['supplier.aop.contract'].search([
            ('contract_version', '!=', 0),
            ('partner_id', '=', purchase_line_id.partner_id.id),
            ('date_start', '<', now_date),
            ('date_end', '>', now_date)
        ])
        return res

