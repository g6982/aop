# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import re
import datetime

WAREHOUSE_PATTERN = '[a-zA-Z0-9]+'
_logger = logging.getLogger(__name__)


class StockLocationToRouteLocation(models.TransientModel):
    _name = 'stock.location.to.route.location.wizard'

    sale_order_id = fields.Many2one('sale.order')
    line_ids = fields.One2many('stock.location.to.route.location.line', 'line_id')

    def find_warehouse_id(self, location_id):

        # FIXME: 规则不确定?
        # code = re.findall(WAREHOUSE_PATTERN, location_id.name)

        code = location_id.display_name.split('/')[0]
        if not code:
            return False

        warehouse_id = self.env['stock.warehouse'].search([
            ('code', '=', code)
        ])
        return warehouse_id

    # 调度到正确的位置上
    def dispatch_order(self):
        for line in self.line_ids:
            warehouse_id = self.find_warehouse_id(line.stock_location_id)
            partner_id = self.sale_order_id.partner_id
            line._create_stock_picking_out(warehouse_id, partner_id)

    @api.model
    def default_get(self, fields_list):
        res = super(StockLocationToRouteLocation, self).default_get(fields_list)
        data = []
        if self._context.get('default_sale_order_id', False):
            stock_quant_ids = self.env['stock.quant'].search([
                ('quantity', '=', 1),
                ('reserved_quantity', '=', 0)
            ])

            sale_order_id = self.env['sale.order'].browse(self._context.get('default_sale_order_id'))

            data = self.parse_wrong_location_vin(sale_order_id, stock_quant_ids)

        if data:
            res['line_ids'] = data
        return res

    # 位置不对的情况的解析
    def parse_wrong_location_vin(self, sale_order_id, stock_quant_ids):
        data = []
        for line_id in sale_order_id.order_line:
            if not line_id.vin:
                continue
            from_location_id = sale_order_id._transfer_district_to_location(line_id.from_location_id)

            # 取最后一条
            stock_location_id = stock_quant_ids.filtered(lambda x: x.lot_id.id == line_id.vin.id)

            stock_location_id = stock_location_id.sorted(lambda x: x.id)[-1] if len(stock_location_id) > 1 else stock_location_id
            route_location_ids = line_id.route_id.rule_ids.mapped('location_src_id').ids

            if not stock_location_id:
                continue

            if from_location_id.id != stock_location_id.location_id.id and stock_location_id.location_id.id not in route_location_ids:
                data.append((0, 0, {
                    'sale_order_line_id': line_id.id,
                    'vin_id': line_id.vin.id,
                    'stock_location_id': stock_location_id.location_id.id,
                    'route_id': line_id.route_id.id,
                    'allowed_to_location_ids': [
                        (6, 0, line_id.route_id.mapped('rule_ids').mapped('location_src_id').ids)]
                }))
        return data


class StockLocationToRouteLocationLine(models.TransientModel):
    _name = 'stock.location.to.route.location.line'

    line_id = fields.Many2one('stock.location.to.route.location.wizard')

    sale_order_line_id = fields.Many2one('sale.order.line')
    vin_id = fields.Many2one('stock.production.lot')
    stock_location_id = fields.Many2one('stock.location')
    to_location_id = fields.Many2one('stock.location')
    route_id = fields.Many2one('stock.location.route')
    allowed_to_location_ids = fields.Many2many('stock.location')

    @api.multi
    def _create_stock_picking_out(self, warehouse_id, partner_id):
        to_location_id = self.to_location_id
        picking_type_id = warehouse_id.out_type_id
        product_id = self.sale_order_line_id.product_id
        vin_id = self.vin_id
        from_location_id = self.stock_location_id
        picking_date = datetime.datetime.now()

        picking_obj = self.env['stock.picking']
        data = {
            'date': picking_date,
            'partner_id': partner_id.id,
            'location_id': from_location_id.id,
            'location_dest_id': to_location_id.id,
            'picking_type_id': picking_type_id.id if picking_type_id else False,
            'scheduled_date': picking_date,
            'picking_type_code': 'internal',
            'vin_id': vin_id.id,
            'origin': self.sale_order_line_id.name
        }

        picking_id = picking_obj.create(data)
        _logger.info({
            'picking_id': picking_id
        })
        self.sale_order_line_id.replenish_picking_id = picking_id.id

        move_data = {
            'name': product_id.name,
            'product_id': product_id.id if product_id else False,
            'product_uom_qty': 1,
            'product_uom': product_id.uom_id.id if product_id else False,
            'location_id': from_location_id.id,
            'location_dest_id': to_location_id.id,
            'state': 'draft',
            'picking_id': picking_id.id,
            'picking_type_id': picking_type_id.id if picking_type_id else False,
            'service_product_id': picking_type_id.service_product_id.id if picking_type_id.service_product_id else False,
            'procure_method': 'make_to_stock',
            'picking_code': 'internal',
            'vin_id': vin_id.id,
        }
        move_id = self.env['stock.move'].create(move_data)

        move_id = move_id.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
        move_id._action_assign()

        # 填充VIN
        picking_id.move_line_ids.lot_id = vin_id.id
        picking_id.move_line_ids.qty_done = 1
        picking_id.move_line_ids.lot_name = vin_id.name