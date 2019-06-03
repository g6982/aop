# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import traceback
import logging



_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderLine, self).default_get(fields)

        if self._context and self._context.get('copy_a_product') and self._context['order_id']:

            order = self.env['sale.order'].browse(self._context['order_id'])
            if order.order_line:
                line = order.order_line[-1]

                value = {'name': line.name,
                 'product_id': line.product_id.id,
                 'service_product_id': line.service_product_id.id,
                 'spare_part_ids': [(6, 0, line.spare_part_ids.ids)],
                 'route_id': line.route_id.id,
                 'product_uom_qty': line.product_uom_qty,
                 'price_unit': line.price_unit,
                 'price_subtotal': line.price_subtotal,
                 'tax_id': [(6, 0, line.tax_id.ids)],
                 'qty_delivered': line.qty_delivered,
                 'qty_invoiced': line.qty_invoiced,
                 'product_uom': line.product_uom.id,
                 'discount': line.discount,
                 'price_total': line.price_total,

                 }

                res.update(value)

        return  res

    def _default_plan_date(self):
        today = fields.Date.today()
        return today

    number = fields.Integer(compute='get_number', store=True)




    vin = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    service_product_id = fields.Many2one('product.product',
                                         string='Product',
                                         #related='route_id.service_product_id',
                                         domain=[('sale_ok', '=', True)],
                                         ondelete='restrict')

    carrier_id = fields.Many2one('delivery.carrier', string='合同')

    contract_id = fields.Many2one('aop.contract', string='合同')



    #carrier_price = fields.Float(string='合同费用', related='carrier_id.fixed_price', store=True, default=0, digits=dp.get_precision('Product Price'))

    carrier_price = fields.Float(string='合同费用', default=0)

    #carrier_price = fields.Monetary(string='合同费用', store=True, readonly=True, compute='_carrier_price')

    #aging = fields.Float('时效', related='carrier_id.aging', store=True,  default=1)

    station_start_end = fields.Char(string='发站-到站')

    receipt_no = fields.Char(string='交接单号')

    plan_date  = membership_start = fields.Date(readonly=True,
        string ='计划日期',  default=_default_plan_date)

    #就是服务产品
    #instruction_type = fields.Selection([
    #    ('global', '全局指令'),
    #    ('otd', 'OTD指令'),
    #    ('composite', '复合指令'),
    #    ('two', '两端指令'),
    #    ('only', '只装车指令'),
    #    ], string='Invoice Status', default='global')

    oems_warehouse = fields.Char(string='主机厂库房')

    oems_order_no = fields.Char(string='订单号')

    income_settle_partner_id = fields.Many2one('res.partner', string='收入结算单位')

    manufacturer_short_name = fields.Char(string='厂商简称')

    vehicle_model_type = fields.Selection([
        ('changan', '长安轿车'),
        ('wulin', '柳州五菱')

        ], string='车型型号', default='changan')

    manufacturer_common_name = fields.Char(string='俗称')

    dealer_partner_id = fields.Many2one('res.partner', string='经销商名称')

    spare_part_ids = fields.Many2many('product.product', string='备品备件')

    #route_id = fields.Many2one(domain=lambda self: self._get_route_id_domain())

    @api.multi
    @api.depends('sequence', 'order_id')
    def get_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.number = number
                number += 1

    #@api.onchange('contract_id')
    def _onchange_route_id(self):

        _logger.info({
            'contract_id': self.contract_id
        })
        #self.carrier_price = self.contract_id.fixed_price

        route_ids = [aop_id.route_id.id for aop_id in self.contract_id.delivery_carrier_ids ]

        if self.order_id.partner_id and self.contract_id:
            return {
                'domain': {
                    'route_id': [('id', 'in', route_ids)]

                }
            }
        else:
            return {
                'domain': []
            }

    #@api.onchange('route_id')
    def _onchange_route_id_by_partner(self):

        res = {
            'domain': []
        }

        if self.order_id.partner_id:
            contract = self.env['aop.contract'].search([
                ('partner_id', '=', self.order_id.partner_id.id)
            ])

            _route_ids = []

            for line in contract.delivery_carrier_ids:
                _route_id = self.env['stock.location.route'].search([
                    ('service_product_id', '=', line.service_product_id.id),
                    ('sale_selectable', '=', True)
                ])
                for route_line in _route_id:
                    _route_ids.append(route_line.id)


            res.update({
                'domain': {
                    'route_id': [('id', 'in', _route_ids)]

                }
            })

        return res


    #@api.onchange('route_id')
    def _onchange_carrier_price(self):


        if self.route_id:

            carrier = self.env['delivery.carrier'].search([
                ('route_id', '=', self.route_id.id)
            ], limit=1)

            if carrier:
                self.carrier_price = carrier.fixed_price




    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.vin = False
            self.product_uom = self.product_id.uom_id.id

        result = super(SaleOrderLine, self).product_id_change()

        return result

    #@api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        pass

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.service_product_id.taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes, line.service_product_id,
                                       line.order_id.partner_shipping_id) if fpos else taxes

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'carrier_price')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.service_product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] + line.carrier_price,
                'price_subtotal': taxes['total_excluded'] + line.carrier_price,
            })

    #@api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        pass

    @api.multi
    @api.onchange('service_product_id')
    def service_product_id_change(self):

        #result = super(SaleOrderLine, self).product_id_change()


        if not self.service_product_id:
            return

        product = self.service_product_id

        vals = {}



        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)


        #return result

    @api.multi
    def _prepare_invoice_line(self, qty):

        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)

        account = self.service_product_id.property_account_income_id or self.service_product_id.categ_id.property_account_income_categ_id

        res.update({
            'product_id': self.service_product_id.id or False,
            'account_id': account.id
        })

        return res


