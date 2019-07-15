# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BundleProductWiz(models.TransientModel):
    _name = "bundle.product.wiz"

    @api.model
    def default_get(self, fields):
        rec = super(BundleProductWiz, self).default_get(fields)
        active_id = self.env[self._context.get('active_model') ].browse(self._context.get('active_id'))
        rec.update({
                'partner_id' : active_id.partner_id.id,
                'pricelist_id':active_id.partner_id.property_product_pricelist.id,
        })
        return rec

    @api.onchange('bundle_id', 'pricelist_id')
    def _onchange_bundle_id(self):
        for rec in self:
            rec.bundle_product_ids = [(6 , 0, rec.bundle_id.bundle_product_ids.ids)]
            rec.uom_id = rec.bundle_id.uom_id.id
            if rec.bundle_id and rec.pricelist_id:
                rec.sale_price = rec.pricelist_id.get_product_price(rec.bundle_id, rec.qty or 1.0, rec.partner_id.id)
            else:
                rec.sale_price = rec.bundle_id.lst_price
            
            
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
    )
    bundle_id = fields.Many2one(
        'product.product',
        string='Add Pack / Bundle',
        required=True,
    )
    qty = fields.Float(
        'Quantity',
        required=True,
        default=1.0,
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist',
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )
    sale_price = fields.Float(
        string='Pack / Bundle Price',
    )
    bundle_product_ids = fields.Many2many(
        'bundle.product',
        string='Bundle Products',
        readonly=True,
    )
    
    @api.multi
    def add_order_line(self):
        if self._context.get('active_model') == 'stock.picking':
            active_obj = self.env['stock.picking'].browse(self._context.get('active_id'))
            move_line_obj = self.env['stock.move']
            for rec in self:
                vals = {
                    'product_id':rec.bundle_id.id,
                    'product_uom_qty':rec.qty,
                    'product_uom':rec.bundle_id.uom_id.id,
                    'picking_id':active_obj.id,
                    'name':rec.bundle_id.name,
                    'location_id':active_obj.location_id.id,
                    'location_dest_id':active_obj.location_dest_id.id
                }
                move_line_obj.create(vals)
                for product in rec.bundle_id.bundle_product_ids:
                    qty = product.qty * rec.qty
                    vals = {
                    'product_id':product.product_id.id,
                    'product_uom_qty':qty,
                    'product_uom':product.uom_id.id,
                    'picking_id':active_obj.id,
                    'name':product.product_id.name,
                    'location_id':active_obj.location_id.id,
                    'location_dest_id':active_obj.location_dest_id.id
                    }
                    move_line_obj.create(vals)
                    
        elif self._context.get('active_model') == 'sale.order':
            active_obj = self.env['sale.order'].browse(self._context.get('active_id'))
            order_line_obj = self.env['sale.order.line']
            for rec in self:
                vals = {
                    'product_id':rec.bundle_id.id,
                    'product_uom_qty':rec.qty,
                    'product_uom':rec.bundle_id.uom_id.id,
                    'price_unit':rec.sale_price,
                    'name':rec.bundle_id.name,
                    'order_id':active_obj.id,
                }
                order_line_obj.create(vals)
                for product in rec.bundle_id.bundle_product_ids:
                    qty = product.qty * rec.qty
                    vals = {
                        'product_id':product.product_id.id,
                        'product_uom_qty':qty,
                        'product_uom':product.uom_id.id,
                        'price_unit':0.0,
                        'name':product.product_id.name,
                        'order_id':active_obj.id,
                    }
                    order_line_obj.create(vals)
