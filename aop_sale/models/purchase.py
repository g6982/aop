# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons import decimal_precision as dp

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _default_plan_date(self):
        today = fields.Date.today()
        return today

    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1)

    vin = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    service_product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True)

    station_start_end = fields.Char(string='发站-到站')

    receipt_no = fields.Char(string='交接单号')

    plan_date = membership_start = fields.Date(readonly=True,
                                               string='计划日期', default=_default_plan_date)

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

    route_id = fields.Many2one('stock.location.route', string='Route',
                               ondelete='restrict')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.vin = False

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.service_product_id.supplier_taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id)
            line.taxes_id = fpos.map_tax(taxes, line.service_product_id, line.order_id.partner_id) if fpos else taxes

    @api.onchange('product_id')
    def onchange_product_id_warning(self):
        pass

    @api.onchange('service_product_id')
    def onchange_service_product_id_warning(self):
        if not self.service_product_id:
            return
        warning = {}
        title = False
        message = False

        product_info = self.service_product_id

        if product_info.purchase_line_warn != 'no-message':
            title = _("Warning for %s") % product_info.name
            message = product_info.purchase_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            if product_info.purchase_line_warn == 'block':
                self.service_product_id = False
            return {'warning': warning}
        return {}

    # @api.multi
    # @api.depends('product_uom', 'product_qty', 'service_product_id.uom_id')
    # def _compute_product_uom_qty(self):
    #     for line in self:
    #         if line.service_product_id.uom_id != line.product_uom:
    #             line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty,
    #                                                                       line.service_product_id.uom_id)
    #         else:
    #             line.product_uom_qty = line.product_qty

    @api.onchange('service_product_id')
    def onchange_service_product_id_warning(self):
        if not self.service_product_id:
            return
        warning = {}
        title = False
        message = False

        product_info = self.service_product_id

        if product_info.purchase_line_warn != 'no-message':
            title = _("Warning for %s") % product_info.name
            message = product_info.purchase_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            if product_info.purchase_line_warn == 'block':
                self.service_product_id = False
            return {'warning': warning}
        return {}

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.service_product_id:
            return
        params = {'order_id': self.order_id}
        seller = self.service_product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if not seller:
            if self.service_product_id.seller_ids.filtered(lambda s: s.name.id == self.partner_id.id):
                self.price_unit = 0.0
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                             self.service_product_id.supplier_taxes_id,
                                                                             self.taxes_id,
                                                                             self.company_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit


    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.service_product_id:
            return

        seller_min_qty = self.service_product_id.seller_ids\
            .filtered(lambda r: r.name == self.order_id.partner_id)\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            # self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_qty = 1.0
            self.product_uom = seller_min_qty[0].product_uom
        else:
            self.product_qty = 1.0

    @api.onchange('service_product_id')
    def onchange_service_product_id(self):
        result = {}
        if not self.service_product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.service_product_id.uom_po_id or self.service_product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.service_product_id.uom_id.category_id.id)]}

        product_lang = self.service_product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        fpos = self.order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(self.service_product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
        else:
            self.taxes_id = fpos.map_tax(self.service_product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result



