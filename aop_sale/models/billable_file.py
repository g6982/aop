# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BillableFile(models.Model):
    _name = 'billable.file'
    _description = 'billable file'
    _sql_constraints = [('unique_name_vin_code', 'unique(name, vin_code, order_line_id)', 'Handover and vin must be unique!')]

    name = fields.Char('Name')
    vin_code = fields.Char('VIN code')
    number = fields.Integer('Number')
    transfer_way = fields.Char('Transfer')
    price_unit = fields.Float('Price unit')
    price_total = fields.Float('Price total')
    diff_amount = fields.Float('Diff amount')
    amount = fields.Float('Amount')
    reimbursement_no = fields.Char('Reimbursement')
    order_line_id = fields.Many2one('sale.order.line')
    invoice_product_type = fields.Selection([
        ('main_product', 'Main product'),
        ('child_product', 'Child product')
    ], required=True, string='Invoice product type', default='main_product')
    vehicle_code = fields.Char('Vehicle code')
    product_id = fields.Many2one('product.product', compute='_compute_product_id', store=True)

    @api.model
    @api.depends('vehicle_code')
    def _compute_product_id(self):
        for line in self:
            if not line.vehicle_code:
                continue
            product_id = self.env['product.product'].search([
                ('default_code', '=', line.vehicle_code[:3])
            ])
            if not product_id or len(product_id) != 1:
                continue
            line.product_id = product_id.id

    # 查找销售订单行，将交接单相同且没有生成回款结算清单的数据，生成回款结算清单
    @api.multi
    def order_line_to_invoice(self):
        # self._null_invoice_order_line_data()
        child_order_line_ids = []
        main_order_line_ids = []
        order_line_amount = {}
        invoice_obj = self.env['sale.advance.payment.inv']
        reconciliation_batch_no = str(time.time())
        for line in self:
            order_line = self.env['sale.order.line'].search([
                ('handover_number', '=', line.name),
                ('vin_code', '=', line.vin_code),
                ('invoice_lines', '=', False)
            ])

            if not order_line or len(order_line) != 1:
                done_order_line = self.env['sale.order.line'].search([
                    ('handover_number', '=', line.name),
                    ('vin_code', '=', line.vin_code),
                ])
                line.order_line_id = done_order_line.id if done_order_line else False
                continue
            # 如果导入的不存在按照产品类型，就按照主产品
            if line.invoice_product_type == 'child_product':
                child_order_line_ids.append(order_line)
            else:
                main_order_line_ids.append(order_line)
            order_line_amount[order_line.id] = line.amount
            line.order_line_id = order_line.id

        if child_order_line_ids:
            invoice_obj.create({
                'selected_order_lines': [(0, 0, {
                    'sale_order_line_id': line.id
                }) for line in child_order_line_ids],
                'invoice_product_type': 'child_product',
                'reconciliation_batch_no': reconciliation_batch_no
            }).create_account_invoice(order_line_amount=order_line_amount)
        if main_order_line_ids:
            invoice_obj.create({
                'selected_order_lines': [(0, 0, {
                    'sale_order_line_id': line.id
                }) for line in main_order_line_ids],
                'invoice_product_type': 'main_product',
                'reconciliation_batch_no': reconciliation_batch_no
            }).create_account_invoice(order_line_amount=order_line_amount)

    def _null_invoice_order_line_data(self):
        sql_delete = '''
            delete from sale_order_line_invoice_rel where invoice_line_id not in (select id from account_invoice_line)
        '''
        self.env.cr.execute(sql_delete)
        self.env.cr.commit()


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    @api.multi
    def do(self, fields, columns, options, dryrun=False):
        res = super(BaseImport, self).do(fields, columns, options, dryrun)

        if not dryrun and self.res_model == 'billable.file':
            records = self.env['billable.file'].browse(res.get('ids'))
            records.order_line_to_invoice()
        return res

    @api.model
    def _convert_import_data(self, fields, options):
        res = super(BaseImport, self)._convert_import_data(fields, options)
        res = self._remove_error_symbol(res)
        return res

    # FIXME： excel 里面出现 \u202d 和 \u202c 这样的特殊字符
    def _remove_error_symbol(self, res):
        try:
            data = res[0]
            data = [[line_data.replace('\u202d', '').replace('\u202c', '') for line_data in line] for line in data]
            return data, res[1]
        except Exception as e:
            return res
