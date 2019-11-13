# -*- coding: utf-8 -*-

from odoo import fields, models, api
import time


class DonePicking(models.Model):
    _name = 'done.picking.log'

    name = fields.Char('Name', default=time.time())

    state = fields.Boolean('State')
    partner_id = fields.Char('Partner')
    product_id = fields.Char('Product')
    vin = fields.Char('VIN')
    from_location_id = fields.Char('From location')
    to_location_id = fields.Char('To location')
    picking_type_id = fields.Char('Picking type')
    quantity_done = fields.Integer('quantity')

    @api.model
    def create(self, vals):
        res = super(DonePicking, self).create(vals)
        # 创建完成后，完成任务/或者创建入库任务

        res.done_stock_picking()
        return res

    # 完成任务：
    # 有计划接车
    # 无计划接车: task_id 值为空
    def done_stock_picking(self):
        pass

