# -*- coding: utf-8 -*-

from odoo import fields, models, api
import time
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class DonePicking(models.Model):
    _name = 'done.picking.log'
    _description = 'WMS done picking log'

    name = fields.Char('Name', default=time.time())

    create_datetime = fields.Datetime('Create time', default=fields.Datetime.now())
    # partner_id = fields.Many2one('res.partner', 'Partner', compute='_compute_partner_id', store=True)
    product_id = fields.Many2one('product.product', 'Product', compute='_compute_product_id', store=True)
    partner_name = fields.Char('Partner')
    product_name = fields.Char('Product name')
    product_model = fields.Char('Product model')
    product_color = fields.Char('Product color')
    product_config = fields.Char('Product config')
    vin = fields.Char('VIN')
    picking_type_name = fields.Char('Picking type')
    quantity_done = fields.Integer('quantity')

    warehouse_code = fields.Char('Warehouse code')
    warehouse_name = fields.Char('Warehouse name')
    task_id = fields.Many2one('stock.picking', 'Stock picking')

    brand_model_name = fields.Char('Brand model name')
    supplier_name = fields.Char('Supplier')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    batch_id = fields.Many2one('stock.picking.batch', 'Picking batch')

    error_message = fields.Char('Error message')

    @api.depends('product_model')
    def _compute_product_id(self):
        for line in self:
            product_id = self.env['product.product'].search([
                ('default_code', '=', line.product_model[:3])
            ])
            if not product_id:
                continue
            line.product_id = product_id[0].id

    # @api.depends('partner_name')
    # def _compute_partner_id(self):
    #     for line in self:
    #         if line.partner_name:
    #             partner_id = self.env['res.partner'].sudo().search([
    #                 ('name', '=', line.partner_name)
    #             ])
    #             if not partner_id:
    #                 continue
    #             line.partner_id = partner_id[0].id

    # 删除接口数据，应该是需要被禁止的
    @api.multi
    def unlink(self):
        raise UserError('You can not delete interface data.')

    @api.model_create_multi
    def create(self, vals):
        res = super(DonePicking, self).create(vals)
        # 创建完成后，完成任务/或者创建入库任务

        try:
            self.done_stock_picking(res)
            res.write({
                'state': 'done'
            })
            return res
        except Exception as e:
            res.write({
                'error_message': e
            })
            return res

    # FIXME: 是否应该使用定时任务呢？还是实时完成
    # 完成任务
    # 有计划接车
    # 无计划接车: task_id 值为空
    def done_stock_picking(self, records):
        warehouse_ids = self._get_warehouse_ids(records)
        task_ids = records.filtered(lambda x: x.task_id)
        null_task_ids = records.filtered(lambda x: not x.task_id)

        self.done_stock_picking_by_task_id(task_ids)
        self.done_stock_picking_without_task_id(null_task_ids, warehouse_ids)

    # 删除采购订单行，完成采购订单
    def _remove_picking_purchase_line(self, batch_id, line_ids):
        picking_ids = line_ids.mapped('task_id')
        all_picking_ids = batch_id.picking_ids

        diff_picking_ids = set(all_picking_ids.ids) - set(picking_ids.ids)

        # 如果存在差异，则进行删除操作，如果没有差异，完成该采购订单
        if diff_picking_ids:
            # 删除调度单
            batch_id.write({
                'picking_ids': [(6, 0, picking_ids.ids)]
            })

            # 删除采购订单行
            delete_purchase_ids = batch_id.picking_purchase_id.order_line.filtered(
                lambda x: x.batch_stock_picking_id.id in list(diff_picking_ids)
            )
            _logger.info({
                'delete purchase line': delete_purchase_ids
            })
            delete_purchase_ids.unlink()

            # 确认采购订单
            batch_id.picking_purchase_id.button_confirm()
        else:
            # 完成采购订单
            batch_id.picking_purchase_id.button_confirm()

    # 完成任务
    # FIXME： 如果完成的数量和实际的不一致，需要把调度订单里面没有反馈回来的数据删除？然后同时删除采购订单行？
    def done_stock_picking_by_task_id(self, line_ids):
        if len(line_ids) > 1:
            # 需要找到任务所在的picking_batch_id，删除没有完成的任务，删除采购订单里面的订单行
            # 一批任务，一定是来自同一个批量调度
            batch_id = line_ids.mapped('batch_id')
            if len(batch_id) != 1:
                line_ids.write({
                    'error_message': 'one than one batch in interface'
                })
            else:
                self._remove_picking_purchase_line(batch_id, line_ids)
        elif len(line_ids) == 1:
            _logger.info({
                'line_ids': line_ids
            })
            # 完成任务, 只完成就绪状态的任务
            if line_ids.task_id.state == 'assigned':
                line_ids.task_id.button_validate()

            # 完成采购单
            # self._confirm_purchase_order(line_ids)
        return True

    # 完成采购单
    def _confirm_purchase_order(self, line_id):
        # 如果所有任务都已完成，则完成采购单
        picking_state = line_id.batch_id.mapped('picking_ids').mapped('state')

        if all(x == 'done' for x in picking_state):
            line_id.batch_id.picking_purchase_id.button_confirm()

    # 无计划接车，直接入库, 需要生成一张入库单
    # 系统内部可能存在接车计划，需要完成系统内部的接车计划。只需要判读目的地和数量？
    def done_stock_picking_without_task_id(self, null_task_ids, warehouse_ids):
        for line_id in null_task_ids:
            self._create_stock_picking(line_id, warehouse_ids)

    # FIXME： 对于常用到的数据，是否需要定时生成缓存呢？
    # 返回获取到的所有产品
    def _get_product_ids(self):
        product_model = self.mapped('product_model')
        products_ids = self.env['product.product'].search([
            ('default_code', 'in', product_model)
        ])
        data = {
            x.default_code: x for x in products_ids
        }
        return data

    # 获取所有合作伙伴
    def _get_partner_ids(self):
        partner_name = self.mapped('partner_name')
        partner_ids = self.env['res.partner'].search([
            ('name', 'in', partner_name)
        ])
        data = {
            x.name: x for x in partner_ids
        }
        return data

    # 获取所有步骤
    def _get_picking_type_ids(self):
        data = {}
        for line in self:
            domain_filter = [
                ('warehouse_id.code', '=', line.warehouse_code),
                ('name', '=', line.picking_type_name)
            ]
            tmp = self.env['stock.picking.type'].sudo().search(domain_filter)
            if not tmp:
                continue
            data.update({
                line.id: tmp[0]
            })
        return data

    def _get_warehouse_ids(self, records):
        warehouse_code = records.mapped('warehouse_code')

        warehouse_ids = self.env['stock.warehouse'].search([
            ('code', 'in', warehouse_code)
        ])

        return {x.code: x for x in warehouse_ids}

    # 获取VIN码
    def get_vin_id_in_stock(self, vin, product_id):
        vin_obj = self.env['stock.production.lot']

        vin_id = vin_obj.search([
            ('name', '=', vin),
            ('product_id', '=', product_id.id)
        ])

        if not vin_id:
            vin_id = vin_obj.create({
                'name': vin,
                'product_id': product_id.id
            })
        return vin_id[0] if vin_id else False

    def find_to_location_id(self, warehouse_location_id, line_id):
        res = self.env['stock.location'].search([
            ('name', '=', line_id.warehouse_name),
            ('location_id', '=', warehouse_location_id.id)
        ])
        return res[0] if res else warehouse_location_id

    # 接车使用仓库默认的入库
    def _create_stock_picking(self, line_id, warehouse_ids):
        picking_obj = self.env['stock.picking']
        stock_move_obj = self.env['stock.move']
        product_id = line_id.product_id
        # partner_id = line_id.partner_id
        warehouse_id = warehouse_ids.get(line_id.warehouse_code)
        picking_type_id = warehouse_id.in_type_id
        warehouse_location_id = warehouse_id.lot_stock_id

        # 供应商 作为source
        from_partner_id = self.env['res.partner'].search([
            ('ref', '=', line_id.brand_model_name)
        ])
        if from_partner_id:
            from_location_id = from_partner_id.property_stock_supplier
        to_location_id = self.find_to_location_id(warehouse_location_id, line_id)
        data = {
            'partner_id': from_partner_id.id,
            'location_id': from_location_id.id,
            'location_dest_id': to_location_id.id,
            'picking_type_id': picking_type_id.id,
            'picking_type_code': 'incoming',
            'date': line_id.create_datetime
        }
        _logger.info({
            'data': data
        })
        vin_id = self.get_vin_id_in_stock(line_id.vin, product_id)
        picking_id = picking_obj.create(data)
        _logger.info({
            'picking_id': picking_id
        })
        move_data = {
            'name': product_id.name + '/income' + str(time.time()),
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
            'picking_code': 'incoming',
            'vin_id': vin_id.id,
        }
        _logger.info({
            'move_data': move_data
        })
        move_id = stock_move_obj.create(move_data)

        move_id = move_id.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
        move_id._action_assign()

        # 填充VIN
        picking_id.move_line_ids.lot_id = vin_id.id
        picking_id.move_line_ids.qty_done = 1
        picking_id.move_line_ids.lot_name = vin_id.name

        picking_id.button_validate()
        return True
