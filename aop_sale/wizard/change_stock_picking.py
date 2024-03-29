# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import random
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ChangeStockPicking(models.TransientModel):
    _name = 'change.stock.picking.wizard'

    picking_id = fields.Many2many('stock.picking')

    line_ids = fields.One2many('change.stock.picking.line.wizard', 'change_wizard_id')

    @api.model
    def default_get(self, fields):
        res = super(ChangeStockPicking, self).default_get(fields)
        ids = self._context.get('active_ids', [])

        if ids:
            self._judge_positive_route(ids)
            res['picking_id'] = [(6, 0, sorted(ids))]
        return res

    # 选择的任务，必须是连续的
    # 选择的任务，起点和终点必须是相同的
    def _judge_positive_route(self, ids):
        if ids:
            picking_ids = self.env['stock.picking'].browse(sorted(ids))
        else:
            picking_ids = self.picking_id

        group_ids = picking_ids.mapped('group_id')

        # 起始位置
        from_location_ids = []
        to_location_ids = []

        group_picking_ids = []

        for group_id in group_ids:
            tmp_picking_ids = picking_ids.filtered(lambda x: x.group_id == group_id)

            group_picking_ids.append(tmp_picking_ids)

            # 没找到，虽然是不可能的，但还是判断一下
            if not tmp_picking_ids:
                continue

            from_location_ids.append(tmp_picking_ids[0].location_id.id)
            to_location_ids.append(tmp_picking_ids[-1].location_dest_id.id)

            if len(tmp_picking_ids) <= 1:
                continue
            self._judge_continue(tmp_picking_ids)

        # 判断起点和终点是否一致
        self._judge_same_location(from_location_ids, to_location_ids)

        # 判断选择的路线，是否是相同长度，以及经过的位置，是否一致
        self._judge_through_location(group_picking_ids)

    # 判断是否连续
    def _judge_continue(self, tmp_picking_ids):
        location_id = tmp_picking_ids.mapped('location_id')
        location_dest_id = tmp_picking_ids.mapped('location_dest_id')

        location_ids = location_id.ids + location_dest_id.ids
        _logger.info({
            'location_ids': location_ids,
            'set': set(location_ids),
            'len': len(tmp_picking_ids)
        })
        # 连续的线段m，长度等于 所有点 n - 1, m = n - 1
        if len(tmp_picking_ids) != len(list(set(location_ids))) - 1:
            raise UserError('You must select continue task.')

    # 判断起点和终点是否一致
    def _judge_same_location(self, from_location_ids, to_location_ids):
        if len(set(from_location_ids)) != 1 or len(set(to_location_ids)) != 1:
            raise UserError('You must select the same from location and to location')

    # 判断选择的路线，是否是相同长度，以及经过的位置，是否一致
    # 只能修改一致的
    def _judge_through_location(self, group_picking_ids):
        for i, j in enumerate(group_picking_ids):
            if i + 1 == len(group_picking_ids):
                break

            if len(group_picking_ids[i]) != len(group_picking_ids[i + 1]):
                raise UserError('You must select the same route.')
            location_id = group_picking_ids[i].mapped('location_id')
            location_dest_id = group_picking_ids[i].mapped('location_dest_id')

            next_location_id = group_picking_ids[i + 1].mapped('location_id')
            next_location_dest_id = group_picking_ids[i + 1].mapped('location_dest_id')

            if set(location_id.ids + location_dest_id.ids) != set(next_location_id.ids + next_location_dest_id.ids):
                raise UserError('The route must have the same location.')

    # move_orig_ids 上一跳, 如果不存在上一跳，则是第一条
    # move_dest_ids 下一跳， 如果不存在下一跳，则是最后一条
    #
    def _get_stock_move_values(self, picking, location_route, index):
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
            'procure_method': move_id.procure_method if index else 'make_to_order',
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

    # 第一跳： 空
    # 第一跳： 原本的记录
    # 最后一跳： 空
    # 最后一跳： 最后一跳记录
    def _link_move_records(self, move_ids, picking_id):
        picking_id = picking_id[-1]
        sorted_move_ids = self._sort_move_records(move_ids)
        for move_id in sorted_move_ids:
            data = {
                'move_dest_ids': [(4, x.id) for x in move_id[2]] if move_id[2] else False,
                'move_orig_ids': [(4, x.id) for x in move_id[0]] if move_id[0] else False
            }
            if move_id[1].id == move_ids[0].id:
                move_id[1].write(data)
            else:
                data.update({
                    'state': 'waiting'
                })
                move_id[1].write(data)

        # 第一条，是之前的记录
        # 最后一条，是最开始的一条的下一跳
        if picking_id.state == 'done':
            move_ids[0].write({
                'move_orig_ids': [(4, x.id)] for x in picking_id.move_lines
            })

        move_ids[-1].write({
            'move_dest_ids': [(4, x.move_dest_ids.id)] for x in picking_id.move_lines
        })

        res = self.env['stock.move'].search([('move_orig_ids', '=', picking_id.move_lines[0].id)])
        res.write({
            'move_orig_ids': [(4, move_ids[-1].id)]
        })

    # 前一条 本条 下一条
    def _sort_move_records(self, move_ids):
        res = []
        for i, j in enumerate(move_ids):
            res.append([
                move_ids[i - 1] if i > 0 else False,
                j,
                move_ids[i + 1] if i < len(move_ids) - 1 else False
            ])
        return res

    # 对picking_id 进行分组
    def _group_picking_ids(self):
        group_ids = self.picking_id.mapped('group_id')
        group_picking_id = []
        for group_id in group_ids:
            tmp_picking_ids = self.picking_id.filtered(lambda x: x.group_id == group_id)
            group_picking_id.append(tmp_picking_ids.sorted(lambda x: x.id))

        return group_picking_id

    # 修改任务
    # 原本： A -> B(stock.move(1,))
    # 修改为: A -> C(stock.move(2,)), C -> D(stock.move(3,)), D -> E(stock.move(4,)), E -> B(stock.move(5,))
    # stock.move(2,) -> next: stock.move(3,)
    #
    # stock.move(3,) -> next: stock.move(4,)
    # stock.move(3,) <- prev: stock.move(2,)
    #
    # stock.move(4,) -> next: stock.move(5,)
    # stock.move(4,) <- prev: stock.move(3,)
    #
    # stock.move(5,) -> next: stock.move()
    # stock.move(5,) <- prev: stock.move(4,)
    def dispatch_stock_picking(self):
        try:
            location_routes = self._get_change_location_route()

            stock_move = self.env['stock.move']
            stock_picking = self.env['stock.picking']

            picking_ids = self._group_picking_ids()
            for picking_id in picking_ids:
                move_ids = []
                index = True

                for location_route in location_routes:
                    # 创建 stock.move
                    move_data = self._get_stock_move_values(picking_id, location_route, index)
                    new_move_id = stock_move.create(move_data)

                    # 创建 stock.picking
                    picking_data = self._get_new_picking_values(picking_id, location_route)
                    new_picking_id = stock_picking.create(picking_data)

                    new_move_id.write({
                        'picking_id': new_picking_id.id
                    })
                    index = False
                    move_ids.append(new_move_id)

                # 将 stock.move 链接起来
                self._link_move_records(move_ids, picking_id)

                # 取消预留
                picking_id[0].move_lines._action_cancel()

                _logger.info({
                    'state': picking_id[0].move_lines.state
                })

                move_ids[0]._action_confirm()
                move_ids[0].picking_id.action_assign()

                # tmp = []
                # for picking_line in picking_id.move_lines:
                #     tmp.append((1, picking_line.id, {
                #         'move_orig_ids': False,
                #         'move_dest_ids': False,
                #     }))
                for pick_id in picking_id:
                    pick_id.write({
                        'state': 'cancel',
                    })
            return True
            # return {
            #     "type": "ir.actions.do_nothing",
            # }
        except Exception as e:
            # 数据回滚
            self._cr.rollback()
            raise UserError(e)

    # 获取需要修改的线路数据
    def _get_change_location_route(self):
        return [(line.from_location, line.to_location) for line in self.line_ids]


class ChangeStockPickingLine(models.TransientModel):
    _name = 'change.stock.picking.line.wizard'

    from_location = fields.Many2one('stock.location')
    to_location = fields.Many2one('stock.location')

    change_wizard_id = fields.Many2one('change.stock.picking.wizard')
