# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import random
import time

_logger = logging.getLogger(__name__)


class ChangeToLocationByOrderLine(models.TransientModel):
    _name = 'change.to.location.by.order.line'

    order_line_ids = fields.Many2many('sale.order.line', string='Order lines')

    line_ids = fields.One2many('change.to.location.by.order.line.detail', 'change_id', 'Line ids')

    @api.model
    def default_get(self, fields_list):
        res = super(ChangeToLocationByOrderLine, self).default_get(fields_list)
        if self.env.context.get('active_ids'):
            res.update({
                'order_line_ids': [(6, 0, self.env.context.get('active_ids'))]
            })
        return res

    # 根据起点和终点。筛选出线段
    def _find_correct_location_area(self, picking_ids, from_location_id, to_location_id):
        '''
        :param picking_ids: 生成的任务
        :param from_location_id:  起点
        :param to_location_id: 目的地
        :return: 在起点和目的地中间的所有任务
        '''
        start_picking_id = picking_ids.filtered(
            lambda x: x.location_id.id == from_location_id.id
        )

        if not start_picking_id:
            raise ValueError('Can not find correct location in all the picking !')

        area_picking_ids = []
        # 找到起点后，找到目的地
        while True:
            if start_picking_id.location_dest_id.id != to_location_id.id:
                area_picking_ids.append(start_picking_id)

                if not start_picking_id.move_lines:
                    break

                # 下一跳
                next_move_id = start_picking_id.move_lines[0].move_dest_ids
                start_picking_id = next_move_id.picking_id
            else:
                area_picking_ids.append(start_picking_id)
                break

        return area_picking_ids

    # stock move 的值
    def _get_stock_move_values(self, picking, location_route):
        move_id = picking[0].mapped('move_lines')[0]
        move_values = {
            'name': move_id.name,
            'company_id': move_id.company_id.id,
            'product_id': move_id.product_id.id,
            'product_uom': move_id.product_id.uom_id.id,
            'product_uom_qty': move_id.product_uom_qty,
            'partner_id': (move_id.group_id and move_id.group_id.partner_id.id) or False,
            'location_id': location_route[0].id,
            'location_dest_id': location_route[-1].id,
            'rule_id': move_id.rule_id.id,
            'procure_method': 'make_to_stock',
            'origin': move_id.name,
            'picking_type_id': move_id.picking_type_id.id,
            'group_id': picking[0].group_id.id,
            'route_ids': [(4, route.id) for route in move_id.route_ids],
            'warehouse_id': move_id.warehouse_id.id,
            'date': move_id.date_expected,
            'date_expected': move_id.date_expected,
            'propagate': move_id.propagate,
            'priority': move_id.priority,
            'vin_id': picking.vin_id.id
        }
        return move_values

    # 新的 picking 的值
    def _get_new_picking_values(self, picking, location_route):
        picking = picking[0]
        return {
            'name': 'DISPATCH/' + picking.name + '/' + str(location_route[0].id) + '/' + str(
                location_route[-1].id) + '/' + str(random.choice(range(int(time.time())))),
            'origin': picking.name,
            'company_id': picking.company_id.id,
            'move_type': picking.group_id and picking.group_id.move_type or 'direct',
            'partner_id': picking.partner_id.id,
            'picking_type_id': picking.picking_type_id.id,
            'location_id': location_route[0].id,
            'location_dest_id': location_route[-1].id,
            'vin_id': picking.vin_id.id
        }

    # 获取需要修改的线路数据
    def _get_change_location_route(self):
        return [(line.from_location_id, line.to_location_id) for line in self.line_ids]

    # 对任务进行关联
    def _link_old_move_and_new_move(self, new_move, picking, position=False):
        picking_move_id = picking.move_lines[0]

        if position == 'start':

            pre_picking_move_id = picking_move_id.move_orig_ids

            # 修改的任务的第一条，是中间节点，即存在上级
            if pre_picking_move_id:
                pre_picking_move_id.write({
                    'move_dest_ids': [(4, new_move.id)]
                })
                new_move.write({
                    'move_orig_ids': pre_picking_move_id.id
                })
        elif position == 'end':
            last_picking_move_id = picking_move_id.move_dest_ids

            # 如果存在下级
            if last_picking_move_id:
                last_picking_move_id.write({
                    'move_orig_ids': [(4, new_move.id)]
                })
                new_move.write({
                    'move_dest_ids': [(4, last_picking_move_id.id)]
                })

    def _link_all_new_move(self, move_ids):
        for index_move, move_id in enumerate(move_ids):
            if move_id == move_ids[-1]:
                continue

            move_id.write({
                'move_dest_ids': [(4, move_ids[index_move + 1].id)]
            })

            move_ids[index_move + 1].write({
                'move_orig_ids': [(4, move_id.id)]
            })

    # 先判断，选择的起点和终点，是否都在路由上
    # 再调度
    def dispatch_location_id_2_new_location_id(self):
        try:
            if not self.line_ids:
                raise ValueError('You must select from/to location')
            start_location_id = self.line_ids[0].from_location_id
            end_location_id = self.line_ids[-1].to_location_id

            stock_move_obj = self.env['stock.move']
            stock_picking_obj = self.env['stock.picking']

            all_new_stock_picking_ids = []
            for sale_order_line_id in self.order_line_ids:
                if not sale_order_line_id.stock_picking_ids:
                    continue

                from_location_ids = sale_order_line_id.route_id.rule_ids.mapped('location_src_id')
                to_location_ids = sale_order_line_id.route_id.rule_ids.mapped('location_id')

                _logger.info({
                    'from_location_id': from_location_ids.mapped('display_name'),
                    'to_location_id': to_location_ids.mapped('display_name'),
                    'start_location_id': start_location_id,
                    'start_name': start_location_id.display_name,
                    'end_location_id': start_location_id,
                    'end_location_name': start_location_id.display_name
                })
                # 验证位置在路由内
                if start_location_id.id not in from_location_ids.ids or end_location_id.id not in to_location_ids.ids:
                    raise ValueError('Value Error')

                picking_ids = sale_order_line_id.stock_picking_ids

                area_picking_ids = self._find_correct_location_area(picking_ids, start_location_id, end_location_id)

                # 筛选出第一条和最后一条

                area_first_picking_id = area_picking_ids[0]
                area_last_picking_id = area_picking_ids[0]

                location_routes = self._get_change_location_route()

                # 新生成的 stock move
                new_dispatch_move_ids = []

                for location_route in location_routes:
                    move_data = self._get_stock_move_values(area_first_picking_id, location_route)
                    new_move_id = stock_move_obj.create(move_data)

                    picking_data = self._get_new_picking_values(area_first_picking_id, location_route)
                    new_picking_id = stock_picking_obj.create(picking_data)

                    new_move_id.write({
                        'picking_id': new_picking_id.id
                    })

                    if new_picking_id:
                        all_new_stock_picking_ids.append(new_picking_id.id)
                    if new_move_id:
                        new_dispatch_move_ids.append(new_move_id)

                if not new_dispatch_move_ids:
                    continue

                # 对生成的所有任务进行关联
                self._link_all_new_move(new_dispatch_move_ids)

                create_first_move_id = new_dispatch_move_ids[0]
                create_last_move_id = new_dispatch_move_ids[0]

                # 关联任务
                self._link_old_move_and_new_move(create_first_move_id, area_first_picking_id, position='first')
                self._link_old_move_and_new_move(create_last_move_id, area_last_picking_id, position='end')

                _logger.info({
                    'area_picking_ids': area_picking_ids
                })
                # 取消之间的所有任务
                for picking_id in area_picking_ids:
                    picking_id.move_lines._do_unreserve()
                    picking_id.move_lines.write({
                        'move_dest_ids': False,
                        'move_orig_ids': False,
                        'state': 'cancel'
                    })
                    # 取消预留
                    # picking_id.move_lines._action_cancel()
                    picking_id.write({
                        'state': 'cancel'
                    })

                # 预留新生成的 stock move
                for new_dispatch_move_id in new_dispatch_move_ids:
                    new_dispatch_move_id[0]._action_confirm()
                    new_dispatch_move_id[0].picking_id.action_assign()

            if all_new_stock_picking_ids:
                view_id = self.env.ref('stock.vpicktree').id
                form_id = self.env.ref('stock.view_picking_form').id

                _logger.info({
                    'all_new_stock_picking_ids': all_new_stock_picking_ids
                })
                # 跳转到生成的新的stock picking tree界面
                return {
                    'name': 'New Picking',
                    'view_type': 'form',
                    'view_id': False,
                    'views': [(view_id, 'tree'), (form_id, 'form')],
                    'res_model': 'stock.picking',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', all_new_stock_picking_ids)],
                    'limit': 80,
                    'target': 'current',
                }
        except Exception as e:
            # 数据回滚
            self._cr.rollback()
            import traceback
            raise ValueError(traceback.format_exc())


class ChangeToLocationByOrderLineDetail(models.TransientModel):
    _name = 'change.to.location.by.order.line.detail'

    change_id = fields.Many2one('change.to.location.by.order.line')
    from_location_id = fields.Many2one('stock.location', 'From')
    to_location_id = fields.Many2one('stock.location', 'To')
