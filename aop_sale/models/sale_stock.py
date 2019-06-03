# -*_ coding :utf-8 -*-

from odoo import models, fields, api
import logging
import traceback
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AopRoute(models.Model):
    _name = 'aop.route'

    name = fields.Char('Name')
    route_line_ids = fields.One2many('aop.route.line', 'aop_route_id', 'Route Line')
    route_id = fields.Many2one('stock.location.route', 'Location route')
    partner_id = fields.Many2one('res.partner', 'Partner')

    aop_id = fields.Many2one('delivery.carrier', string='交货方式')

    product_id = fields.Many2one('product.product', string='服务产品', domain=[('type', '=', 'service')])

    # 线路的 ID
    def _parse_aop_route_line(self, route_line_ids):
        '''
        :param route_line_ids:
        :return: 顺序的位置
        '''
        route_data = []
        for line in route_line_ids.sorted('sequence'):
            route_data.append(line)

        return route_data

    # 仓库的 ID
    def _parse_warehouse_id(self):
        warehouse_id = []
        for line in self.route_line_ids:
            if line.warehouse_id:
                warehouse_id.append(line.warehouse_id.id)
        return list(set(warehouse_id))

    # TODO 移除
    def _get_picking_id(self, warehouse):
        res = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', warehouse.id),
            ('name', '=', u'交货单')
        ], limit=1)
        return res

    # 线路主体
    def _get_location_route_data(self, warehouse, route_data):
        line_data = {
            'name': route_data[0].partner_id.display_name + ' -> ' + route_data[-1].des_partner_id.display_name,
            'product_selectable': True,
            'sale_selectable': True,
            'partner_id': self.partner_id.id,
            'warehouse_selectable': True,
            'warehouse_ids': [(6, 0, warehouse)],
        }
        return line_data

    # 路线行
    def _get_line_data(self, location_src, location_des, picking_id):
        res = {
            'name': location_src.display_name + ' -> ' + location_des.display_name,
            'action': 'pull',
            'picking_type_id': picking_id.id,
            'procure_method': 'make_to_order',
            'location_src_id': location_src.id,
            'location_id': location_des.id,
            'group_propagation_option': 'propagate',
            'propagate': True,
        }
        return res

    def _get_location_route_line_data(self, route_data):
        route_res = []

        for line_id in route_data:
            src_location, des_location = self._get_location_from_picking_type(line_id.picking_type_id)
            route_res.append(
                (0, 0,
                 self._get_line_data(src_location, des_location, line_id.picking_type_id)
                 )
            )
        return route_res

    @api.multi
    def generate_route_by_location(self):
        try:
            if self.route_id:
                raise UserError(u'已经存在路线')
            if not self.route_line_ids:
                raise UserError(u'请先定义线路明细行')

            warehouse_id = self._parse_warehouse_id()
            _logger.info({
                'warehouse_id': warehouse_id
            })
            route_data = self._parse_aop_route_line(self.route_line_ids)
            route_body = self._get_location_route_data(warehouse_id, route_data)

            route_line_data = self._get_location_route_line_data(route_data)

            route_body.update({
                'rule_ids': route_line_data
            })
            res = self.env['stock.location.route'].create(route_body)
            self.write({
                'route_id': res.id
            })
        except Exception as e:
            self.env.cr.rollback()
            raise UserError(traceback.format_exc())

    def _get_location_from_picking_type(self, picking_type):
        if not picking_type.default_location_src_id and not picking_type.default_location_dest_id:
            raise UserError(u'请先在作业类型[ {} ],上定义默认源位置 和 默认目的位置'.format(
                picking_type.name
            ))
        return picking_type.default_location_src_id, picking_type.default_location_dest_id

    def delete_route(self):
        if self.route_id:
            self.route_id.unlink()
        else:
            raise UserError(u'请先生成路由')


class AopRouteLine(models.Model):
    _name = 'aop.route.line'
    _order = 'sequence'

    name = fields.Char('Name')
    aop_route_id = fields.Many2one('aop.route', 'Route')
    sequence = fields.Integer('Sequence', default=0)
    # location_id = fields.Many2one('stock.location', 'Stock location')
    # des_location_id = fields.Many2one('stock.location', 'Destination')
    partner_id = fields.Many2one('res.partner', 'Src partner', related='picking_type_id.src_partner_id')
    des_partner_id = fields.Many2one('res.partner', 'Destination', related='picking_type_id.des_partner_id')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking type')
