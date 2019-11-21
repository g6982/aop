# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
import time
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Stock batch')

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({
            'origin_purchase_id': self.id
        })
        return res

    # 完成的同时，完成 batch
    # 跨公司 sudo
    # 如果没有明细，则生成明细
    @api.multi
    def button_confirm(self):
        try:
            # 服务产品
            res = super(PurchaseOrder, self).button_confirm()
            return res
        except Exception as e:
            import traceback
            self._cr.rollback()
            raise UserError(traceback.format_exc())

    @api.multi
    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force)
        if 'service' in self.mapped('order_line').mapped('product_id').mapped('type'):
            for order_id in self:

                order_id._create_stock_move_by_purchase()

                # 排序过后的就绪状态的任务
                batch_picking_ids = order_id.mapped('stock_picking_batch_id').sudo().picking_ids.sorted(
                    lambda x: x.id).filtered(lambda x: x.state == 'assigned')

                for picking_id in batch_picking_ids:
                    self.sudo()._fill_serial_no(picking_id)
                    picking_id.sudo().action_assign()
                    picking_id.sudo().button_validate()
                order_id.mapped('stock_picking_batch_id').done()
        return res

    # 生成 stock.move
    def _create_stock_move_by_purchase(self):
        stock_move_obj = self.env['stock.move']
        stock_move_data = []

        picking_ids = []
        for picking_id in self.mapped('stock_picking_batch_id').picking_ids:
            if not picking_id.move_ids_without_package and picking_id.state != 'done':
                picking_ids.append(picking_id.id)

        for line_id in self.order_line:
            if not hasattr(line_id, 'batch_stock_picking_id'):
                continue

            if line_id.batch_stock_picking_id.id not in picking_ids:
                continue

            vin_obj = self.env['stock.production.lot']
            vin_domain = [('name', '=', line_id.vin_code), ('product_id', '=', line_id.transfer_product_id.id)]

            vin_id = vin_obj.search(vin_domain)
            if not vin_id:
                vin_id = vin_obj.create({
                    'name': line_id.vin_code,
                    'product_id': line_id.transfer_product_id.id
                })
            data = {
                'product_id': line_id.transfer_product_id.id,
                'product_uom': line_id.transfer_product_id.uom_id.id,
                'product_uom_qty': 1,
                'name': line_id.transfer_product_id.name,
                'vin_id': vin_id.id,
                'picking_id': line_id.batch_stock_picking_id.id,
                'picking_type_id': line_id.batch_stock_picking_id.picking_type_id.id,
                'location_id': line_id.batch_stock_picking_id.location_id.id,
                'location_dest_id': line_id.batch_stock_picking_id.location_dest_id.id,
            }
            stock_move_data.append(data)
            # line_id.batch_stock_picking_id.write({
            #     'vin_id': vin_id.id
            # })

        # 生成 stock.move
        if stock_move_data:
            res = stock_move_obj.create(stock_move_data)

        # 完成且只完成就绪状态的任务
        assign_picking_ids = self.order_line.mapped('batch_stock_picking_id').filtered(lambda x: x.state == 'assigned')
        assign_picking_ids.action_confirm()

    # 填充批次号
    def _fill_serial_no(self, picking_id):
        for move_id in picking_id.move_lines:
            for line in move_id.move_line_ids:
                line.write({
                    'lot_id': move_id.vin_id.id,
                    'qty_done': line.product_uom_qty
                })


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    transfer_product_id = fields.Many2one('product.product', 'Transfer product')

    vin_code = fields.Char('VIN')

    vehicle_number = fields.Char(string='Vehicle number')

    transfer_way = fields.Char('Way')

    train_type = fields.Char(string='Train type')

    cargo_line = fields.Char(string='Cargo line')

    box_number = fields.Char(string='Box number')

    batch_stock_picking_id = fields.Many2one('stock.picking')

    service_contract_price = fields.Float('Service contract price')

    picking_id = fields.Many2one('stock.picking', 'Picking')


