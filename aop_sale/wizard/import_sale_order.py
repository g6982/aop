# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
import binascii
import traceback

_logger = logging.getLogger(__name__)


class ImportSaleOrder(models.TransientModel):
    _name = 'import.sale.order.wizard'

    partner_id = fields.Many2one('res.partner', 'Partner')
    file = fields.Binary('File')

    # 读文件
    def _parse_import_file(self):
        data = binascii.a2b_base64(self.file)
        book = xlrd.open_workbook(file_contents=data or b'')
        sheet_data = book.sheet_by_index(0)
        return sheet_data

    # 导入订单
    def start_import_sale_order(self):
        return self._import_sale_order()

    def _import_sale_order(self):
        try:
            sale_order = self.env['sale.order']
            sheet_data = self._parse_import_file()
            order_data= self._parse_order_data()
            line_data = self._parse_order_line_data(sheet_data)
            order_data.update({
                'order_line': line_data
            })
            sale_order.create(order_data)
            return {
                "type": "ir.actions.do_nothing",
            }
        except Exception as e:
            self._cr.rollback()
            raise UserError(traceback.format_exc())

    # 订单主体的数据
    def _parse_order_data(self):
        order_value = {
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id
        }
        return order_value

    # product_id
    # service_product_id
    # from_location
    # to_location
    # vin
    # name
    # product_uom_qty
    # product_uom
    # price_unit
    # tax_id
    # 订单行的数据
    def _parse_order_line_data(self, sheet_data):
        line_values = []
        for x in range(6, sheet_data.nrows - 1):
            product_id = self._find_product_id(sheet_data.cell_value(x, 6), sheet_data.cell_value(x, 7))
            from_location_id = self._find_from_to_location(sheet_data.cell_value(x, 2))
            to_location_id = self._find_from_to_location(sheet_data.cell_value(x, 11))

            if not product_id or not from_location_id or not to_location_id or len(product_id) > 1:
                continue
            vin_id = self._find_vin_id(sheet_data.cell_value(x, 4), product_id)
            line_data = (0, 0, {
                'product_id': product_id.id,
                'service_product_id': False,
                'from_location_id': from_location_id.id,
                'to_location_id': to_location_id.id,
                'vin': vin_id.id if vin_id else False,
                'name': product_id.name,
                'product_uom_qty': 1,
                'product_uom': product_id.uom_id.id,
                'price_unit': 1
            })
            line_values.append(line_data)
            print(line_values)
        return line_values

    def _find_product_id(self, product_type, product_color):
        # 颜色
        color_id = self.env['product.attribute'].search([
            ('name', '=', u'颜色名称'),
            ('value_ids.name', '=', product_color)
        ])
        # 车型
        type_id = self.env['product.attribute'].search([
            ('name', '=', u'车型名称'),
            ('value_ids.name', '=', product_type)
        ])
        _logger.info({
            'type_id': type_id,
            'color_id': color_id
        })
        # color_attribute_ids = self.env['product.attribute.value'].search([
        #     ('attribute_id', '=', color_id.id),
        #     ('name', '=', product_color)
        # ])
        # type_attribute_ids = self.env['product.attribute.value'].search([
        #     ('attribute_id', '=', type_id.id),
        #     ('name', '=', product_type)
        # ])

        product_id = self.env['product.product'].search([
            ('attribute_value_ids', '=', color_id.id),
            ('attribute_value_ids', '=', type_id.id)
        ])
        return product_id if product_id else False

    def _find_from_to_location(self, name):
        partner_id = self.env['res.partner'].search([
            ('name', '=', name),
            ('parent_id', '=', False)
        ])
        return partner_id if partner_id else False

    def _find_vin_id(self, vin_code, product_id):
        vin_id = self.env['stock.production.lot'].search([
            ('name', '=', vin_code),
            ('product_id', '=', product_id.id)
        ])
        return vin_id if vin_id else False
