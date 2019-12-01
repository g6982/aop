#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockPickingChangeToBatch(models.TransientModel):
    _name = 'stock.picking.change.to.batch'

    picking_ids = fields.Many2many('stock.picking', 'Picking')
    to_location_id = fields.Many2one('stock.location', 'Change to location')

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking type')
    partner_id = fields.Many2one('res.partner', 'Partner')

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(StockPickingChangeToBatch, self).default_get(fields_list)
    #     if self.env.context.get('active_ids'):
    #         res.update({
    #             'picking_ids': [(6, 0, self.env.context.get('active_ids'))]
    #         })
    #     return res

    # 验证数据，只能选择同一个源和目的地的数据
    def _validate_choose_picking(self, picking_ids):
        from_location_ids = picking_ids.mapped('real_stock_location_id')
        to_location_ids = picking_ids.mapped('location_dest_id')

        if len(set(from_location_ids.ids)) != 1 and len(set(to_location_ids)) != 1:
            raise ValidationError('You must choose same from location and to location !')

    @api.multi
    def change_and_attach_pickings(self):
        self.ensure_one()
        picking_ids = self.env.context.get('active_ids')

        # 任务
        picking_ids = self.env['stock.picking'].browse(picking_ids)

        # 验证数据
        self._validate_choose_picking(picking_ids)

        # 起始位置信息
        from_location_id = list(set(picking_ids.mapped('real_stock_location_id')))[0]

        # 新的目的地的位置信息
        new_to_location_id = self.to_location_id

        self._create_stock_picking(picking_ids, from_location_id, new_to_location_id)

    # 先根据位置，创建任务，再创建调度单
    # 创建任务的时候，需要将原先的任务与新创建的任务进行关联，同时修改原先任务的stock.move 的 location_id
    def _change_origin_stock_picking_move_location(self):
        pass

    # stock.picking 的数据
    def _get_new_stock_picking_data(self, picking_id, from_location_id, new_to_location_id):
        data = {
            'partner_id': picking_id.partner_id.id,
            'location_id': from_location_id.id,
            'location_dest_id': new_to_location_id.id,
            'scheduled_date': picking_id.scheduled_date,
            'procure_method': 'make_to_stock',
            'picking_type_id': self.picking_type_id.id
        }
        return data

    # stock.move 的数据
    def _get_new_stock_picking_move_data(self, picking_id, from_location_id, new_to_location_id):
        # move 有且仅有一条数据
        move_id = picking_id.move_lines
        move_id = move_id[0]

        move_values = {
            'name': move_id.name,
            'company_id': move_id.company_id.id,
            'product_id': move_id.product_id.id,
            'product_uom': move_id.product_uom.id,
            'partner_id': picking_id.partner_id.id,
            'product_uom_qty': 1,
            'location_id': from_location_id.id,
            'location_dest_id': new_to_location_id.id,
            'procure_method': 'make_to_stock',
            'origin': move_id.name,
            'picking_type_id': self.picking_type_id.id,
            'warehouse_id': move_id.warehouse_id.id,
            'date': move_id.date_expected,
            'date_expected': move_id.date_expected,
            'propagate': move_id.propagate,
            'priority': move_id.priority,
        }
        return move_values

    # 创建批量调度
    def _create_stock_picking_batch(self):
        # 批量调度
        stock_picking_batch_obj = self.env['stock.picking.batch']

        data = {
            'un_limit_partner_id': self.partner_id.id,
            'user_id': self.env.user.id
        }

        res = stock_picking_batch_obj.create(data)
        return res

    # 创建新的任务
    @api.multi
    def _create_stock_picking(self, picking_ids, from_location_id, new_to_location_id):
        new_picking_ids = []

        # 任务
        stock_picking_obj = self.env['stock.picking']

        for picking_id in picking_ids:
            new_picking_data = self._get_new_stock_picking_data(picking_id, from_location_id, new_to_location_id)
            new_move_data = self._get_new_stock_picking_move_data(picking_id, from_location_id, new_to_location_id)

            new_picking_data.update({
                'move_ids_without_package': [(0, 0, new_move_data)]
            })

            res = stock_picking_obj.create(new_picking_data)
            new_picking_ids.append(res.id)

            # 将原本的 picking 关联到 新创建的 picking
            # move_orig_ids
            # move_dest_ids

            move_id = picking_id.move_lines
            move_id = move_id[0]

            move_id.location_id = new_to_location_id.id

        picking_batch_id = self._create_stock_picking_batch()
        picking_batch_id.write({
            'picking_ids': [(6, 0, new_picking_ids)]
        })

        view_id = self.env.ref('stock_picking_batch.stock_picking_batch_tree').id
        form_id = self.env.ref('stock_picking_batch.stock_picking_batch_form').id
        return {
            'name': 'Picking batch',
            'view_type': 'form',
            'view_id': False,
            'views': [(view_id, 'tree'), (form_id, 'form')],
            'res_model': 'stock.picking.batch',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', picking_batch_id.ids)],
            'limit': 80,
            'target': 'current',
        }