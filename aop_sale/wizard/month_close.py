# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import time
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class MonthClose(models.TransientModel):
    _name = 'month.close.wizard'

    period_id = fields.Many2one('account.period', string='Period', required=True)

    # 1. 将没有生成结算清单的销售订单行，生成结算清单
    # 2. 标记月结状态
    def start_generate_monthly(self):
        if self.period_id.monthly_state:
            raise UserError('Please cancel monthly first')

        self._null_invoice_order_line_data()
        sale_order_line_ids = self.find_sale_order_not_invoice()

        if sale_order_line_ids:
            # 月结操作的时候，需要生成收入确认的值
            context = {
                'active_ids': [x.mapped('order_id').id for x in sale_order_line_ids],
                'period_id': self.period_id.id,
                'monthly_confirm_invoice': True
            }
            return {
                'name': _('Make invoice'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'sale.advance.payment.inv',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        self._purchase_create_invoice()
        self.period_id.monthly_state = True

    def cancel_monthly(self):
        self.period_id.monthly_state = False

    # FIXME: 不知道为啥many2many 的值没有被删除
    def _null_invoice_order_line_data(self):
        sql_delete = '''
            delete from sale_order_line_invoice_rel where invoice_line_id not in (select id from account_invoice_line)
        '''
        self.env.cr.execute(sql_delete)
        self.env.cr.commit()

    # 筛选当前期间内的数据
    def find_sale_order_not_invoice(self):
        # res = self.env['sale.order.line'].search([
        #     ('invoice_lines', '=', False),
        #     ('write_date', '>=', self.period_id.date_start),
        #     ('write_date', '<=', self.period_id.date_stop),
        #     ('order_id.state', '!=', 'draft')
        # ])
        res = self.env['sale.order.line'].search([
            ('invoice_lines', '=', False),
            ('write_date', '>=', self.period_id.date_start),
            ('write_date', '<=', self.period_id.date_stop),
            ('picking_confirm_date', '!=', False)
        ])
        if not res:
            return False
        line_ids = []
        for sale_line_id in res:
            _logger.info({
                'state': sale_line_id.stock_picking_ids.mapped('state')
            })
            if any(x.state != 'done' for x in sale_line_id.stock_picking_ids):
                continue
            line_ids.append(sale_line_id)

        return line_ids

    # 采购单生成成本结算清单
    def _purchase_create_invoice(self):
        data = []
        purchase_ids = self.env['purchase.order'].search([('invoice_count', '<=', 0), ('state', '=', 'purchase')])
        partner_ids = self._parse_partner_id(purchase_ids)

        reconciliation_batch_no = str(time.time())
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
                'reconciliation_batch_no': partner_ids.get(line.partner_id.id, reconciliation_batch_no),
            }
            line_data = []
            for line_id in line.order_line:
                tmp = self._prepare_invoice_line_from_po_line(line_id)
                line_data.append((0, 0, tmp))
            invoice_data.update({
                'invoice_line_ids': line_data
            })
            data.append(invoice_data)
        invoice_obj = self.env['account.invoice']
        invoice_ids = invoice_obj.create(data)

        self._create_purchase_invoice_no(invoice_ids)

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
                    'invoice_line_ids': [(4, line_id.id) for line_id in purchase_invoice_ids.mapped('invoice_line_ids')]
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
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
        invoice_line = self.env['account.invoice.line']
        # date = self.date or self.date_invoice
        date = False
        journal_domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', line.order_id.company_id.id),
            ('currency_id', '=', line.order_id.partner_id.property_purchase_currency_id.id),
        ]
        journal_id = self.env['account.journal'].search(journal_domain, limit=1)
        price_unit = line.price_unit
        contract_price = self._get_contract_price(line)
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name + ': ' + line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': contract_price,
            'quantity': 1,
            'discount': 0.0,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids,
            'tmp_estimate': contract_price,
            'contract_price': contract_price,
            'location_id': line.batch_stock_picking_id.location_id.id,
            'location_dest_id': line.batch_stock_picking_id.location_dest_id.id,
            'sale_order_line_id': line.sale_line_id.id if line.sale_line_id else False,
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id, self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

    def _parse_partner_id(self, purchase_ids):
        partner_ids = purchase_ids.mapped('partner_id')

        data = {}

        for partner_id in partner_ids:
            code = self.env['ir.sequence'].next_by_code('seq_invoice_supplier_code')
            data.update({
                partner_id.id: self.part_partner_id_code(partner_id, code)
            })
        return data

    def part_partner_id_code(self, partner_id, code):
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
