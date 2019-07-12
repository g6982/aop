# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BundleProduct(models.Model):
    _name = 'bundle.product'

    @api.onchange('product_id')
    def _product_onchange(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id.id
            rec.unit_price = rec.product_id.lst_price

    @api.depends('unit_price','qty')
    def _compute_sale_price(self):
        for rec in self:
            rec.sale_price = rec.qty * rec.unit_price

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    qty = fields.Float(
        string='Quantity',
        default=1.0,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Uom',
    )
    product_template_id = fields.Many2one(
        'product.template',
        string='Product Bundle',
    )
    unit_price = fields.Float(
        string='Unit Price',
    )
    sale_price = fields.Float(
        string='Sub Total',
        compute='_compute_sale_price'
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends('bundle_product_ids')
    def _compute_total(self):
        for rec in self:
            for product in rec.bundle_product_ids:
                rec.total += product.sale_price

    bundle_product = fields.Boolean(
        'Is Bundled',
    )
    bundle_product_ids = fields.One2many(
        'bundle.product',
        'product_template_id',
    )
    total = fields.Float(
        string="Total",
        compute="_compute_total",
    )

    @api.model
    def create(self, vals):
        bundle_product = vals.get('bundle_product', False)
        attribute_line_ids = vals.get('attribute_line_ids', False)
        if bundle_product and attribute_line_ids:
            raise ValidationError(_('You can not set variant for bundled product.'))
        return super(ProductTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            bundle_product = vals.get('bundle_product', False) or rec.bundle_product
            attribute_line_ids = vals.get('attribute_line_ids', False) or rec.attribute_line_ids
            if bundle_product and attribute_line_ids:
                raise ValidationError(_('You can not set variant for bundled product.'))
        return super(ProductTemplate, self).write(vals)
