# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # car_no_ids = fields.Many2many('stock.quant.package', string='Loading number')

    un_limit_partner_id = fields.Many2one('res.partner', string='Vendor')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    allow_partner_ids = fields.Many2many('res.partner',
                                         string='Allow partners',
                                         store=True,
                                         compute='_compute_allow_partner_ids')
    limit_state = fields.Selection([
        ('limit', 'Limit'),
        ('un_limit', 'Un-limit')
    ], dafault='un_limit')

    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase', copy=False)
    dispatch_type = fields.Selection([('center_type', 'Center'),
                                      ('train_type', 'train'),
                                      ('highway_type', 'highway')
                                      ],
                                     string='Dispatch type',
                                     store=True)
    plan_number = fields.Integer(string='Plan number', default=1)

    vehicle_number = fields.Char(string='Vehicle number')

    mount_car_plan_ids = fields.One2many('mount.car.plan', 'stock_picking_batch_id', string='Mount plan')

    # 生成采购订单，采购：服务产品
    def create_purchase_order(self):
        try:
            data, service_product_context = self._get_purchase_data()

            if service_product_context:
                return {
                    'name': _(u'测试'),
                    'view_type': 'form',
                    "view_mode": 'form',
                    'res_model': 'fill.service.product.wizard',
                    'type': 'ir.actions.act_window',
                    'context': service_product_context,
                    'target': 'new',
                }

            # 跨公司创建
            res = self.env['purchase.order'].sudo().create(data)

            self.write({
                'picking_purchase_id': res.id
            })
        except Exception as e:
            self._cr.rollback()
            import traceback
            raise UserError(traceback.format_exc())

    # 根据条件。获取值
    def get_vendor_id(self):
        if self.limit_state == 'limit' and self.allow_partner_ids:
            return self.partner_id.id
        else:
            return self.un_limit_partner_id.id

    # 跨公司生成采购订单，对应的客户，即是对应公司的客户
    def _get_purchase_data(self):
        vendor = self.get_vendor_id()
        if not vendor:
            raise UserError('You must check selection records.')

        res = {
            'name': str(time.time()),
            'partner_id': vendor,
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_batch_id': self.id,
            'company_id': self._match_company_id(self.partner_id)
        }

        data = self._get_purchase_line_data()
        line_data, lost_service_product_id = data[0], data[-1]

        service_product_context = []
        if lost_service_product_id:
            service_product_context = {
                'default_stock_picking_batch_id': self.id,
                'default_wizard_line_ids': [(0, 0, {
                    'picking_id': line.id,
                    'from_location_id': line.location_id.id,
                    'to_location_id': line.location_dest_id.id
                }) for line in lost_service_product_id],
            }
        res.update({
            'order_line': line_data
        })
        return res, service_product_context

    # 服务产品
    # 产品不能添加公司属性值
    def _get_purchase_line_data(self):
        res = []

        lost_service_product_id = []

        for picking in self.picking_ids:
            for _ in range(picking.picking_incoming_number) if picking.picking_incoming_number > 1 else []:
                res, lost_service_product_id = self._parse_purchase_line_data(picking, lost_service_product_id, res)
            if picking.picking_incoming_number <= 1:
                res, lost_service_product_id = self._parse_purchase_line_data(picking, lost_service_product_id, res)

        return [res, lost_service_product_id]

    def _parse_purchase_line_data(self, picking, lost_service_product_id, res):
        carrier_id = self._parse_service_product_supplier(picking)

        service_product_id = carrier_id.service_product_id if carrier_id else False

        if not service_product_id:
            lost_service_product_id.append(picking)

        for line_id in picking.move_lines:
            data = {
                'product_id': service_product_id.id if service_product_id else line_id.picking_type_id.service_product_id.id if line_id.picking_type_id.service_product_id else False,
                'transfer_product_id': line_id.product_id.id,
                # 'service_product_id': service_product_id.id if service_product_id else False,
                'product_qty': line_id.product_uom_qty,
                'sale_line_id': line_id.sale_order_line_id.id,
                'name': picking.picking_type_id.display_name,
                'date_planned': fields.Datetime.now(),
                'service_contract_price': carrier_id.product_standard_price if carrier_id else 0,
                'price_unit': 0,
                'product_uom': service_product_id.uom_id.id if service_product_id else line_id.picking_type_id.service_product_id.uom_id.id if line_id.picking_type_id.service_product_id else False,
                'batch_stock_picking_id': picking.id,
                'vin_code': line_id.vin_id.name if line_id.vin_id else False
            }
            res.append((0, 0, data))
        if not picking.move_lines and service_product_id:
            data = {
                'product_id': service_product_id.id,
                'product_qty': 1,
                'name': service_product_id.name,
                'product_uom': service_product_id.uom_id.id,
                'batch_stock_picking_id': picking.id,
                'carrier_id.product_standard_price if carrier_id else ': carrier_id.product_standard_price,
                'price_unit': 0,
                'date_planned': fields.Datetime.now(),
            }
            res.append((0, 0, data))
        lost_service_product_id = list(set(lost_service_product_id))
        return res, lost_service_product_id

    # 查找供应商合同条款
    def _parse_service_product_supplier(self, picking):
        contract_domain = [
            ('supplier_contract_id.partner_id', '=', self.partner_id.id),
            ('from_location_id', '=', picking.location_id.id),
            ('to_location_id', '=', picking.location_dest_id.id)
        ]
        delivery_carrier_id = self.env['delivery.carrier'].search(contract_domain)
        return delivery_carrier_id[0] if delivery_carrier_id else False

    def _match_company_id(self, partner_id):
        res = self.env['res.company'].sudo().search([('code', '=', partner_id.ref)])
        return res.id if res else False

    @api.multi
    @api.depends('picking_ids')
    def _compute_allow_partner_ids(self):
        self.ensure_one()
        sale_order_line_ids = self.mapped('picking_ids').mapped('sale_order_line_id') if self.mapped('picking_ids') else False

        if not sale_order_line_ids:
            self.allow_partner_ids = False
            self.limit_state = 'un_limit'
        else:
            customer_contract_ids = sale_order_line_ids.mapped('customer_contract_id')
            if not customer_contract_ids:
                self.allow_partner_ids = False
                self.limit_state = 'un_limit'
            res = self.env['supplier.aop.contract'].search([
                ('allow_customer_contract_ids', 'in', customer_contract_ids.ids)
            ])
            _logger.info({
                'res': res,
                'partner_ids': res.mapped('partner_id').ids
            })
            if not res:
                self.allow_partner_ids = False
                self.limit_state = 'un_limit'
            else:
                self.allow_partner_ids = [(6, 0, res.mapped('partner_id').ids)]
                self.limit_state = 'limit'


class MountCarPlan(models.Model):
    _name = "mount.car.plan"

    name = fields.Char(string='Vehicle model')

    layer_option = fields.Selection([
        ('upper_layer', 'Upper layer'),
        ('lower_layer', 'Lower layer')
    ], string='Layer')

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Dispatch order')