# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
import binascii
import traceback
import re

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
            order_data = self._parse_order_data()
            partner_data = self._parse_partner_id(sheet_data)
            product_data = self._parse_product_data(sheet_data)
            line_data = self._parse_order_line_data(sheet_data, product_data, partner_data)
            order_data.update({
                'order_line': line_data,
            })
            _logger.info({
                'partner_data': partner_data
            })
            res = sale_order.create(order_data)

            view_id = self.env.ref('sale.view_quotation_tree_with_onboarding').id
            form_id = self.env.ref('sale.view_order_form').id

            # 跳转到导入成功后的tree界面
            return {
                'name': 'Order',
                'view_type': 'form',
                'view_id': False,
                'views': [(view_id, 'tree'), (form_id, 'form')],
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', res.ids)],
                'limit': 80,
                'target': 'current',
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
    def _parse_order_line_data(self, sheet_data, product_data, partner_data):
        line_values = []
        for x in range(6, sheet_data.nrows - 1):
            if not sheet_data.cell_value(x, 1):
                continue

            product_id = self._find_product_id(sheet_data.cell_value(x, 6), product_data)
            from_location_id = self._find_from_to_location(sheet_data.cell_value(x, 2), partner_data)
            to_location_id = self._find_from_to_location(sheet_data.cell_value(x, 10), partner_data)
            # _logger.info({
            #     'product_id': product_id,
            #     'from_location_id': from_location_id,
            #     'to_location_id': to_location_id,
            #     'from': sheet_data.cell_value(x, 2),
            #     'to': sheet_data.cell_value(x, 11)
            # })
            if not product_id:
                continue
            vin_id = self._find_vin_id(sheet_data.cell_value(x, 4), product_id)

            line_data = (0, 0, {
                'product_id': product_id.id,
                'service_product_id': False,
                'from_location_id': from_location_id.id if from_location_id else False,
                'to_location_id': to_location_id.id if to_location_id else False,
                'vin': vin_id.id if vin_id else False,
                'name': product_id.name,
                'product_uom_qty': 1,
                'product_uom': product_id.uom_id.id,
                'price_unit': 1
            })
            line_values.append(line_data)
            _logger.info({
                'line_data': line_data
            })
            # print(line_values)
        return line_values

    def _parse_product_data(self, sheet_data):
        product_dict = {}
        # partner_name = sheet_data.row_values(4)
        product_name = sheet_data.col_values(6)

        if not product_name:
            return False

        product_name = list(set(product_name[6:]))

        product_obj = self.env['product.product']

        for p_name in product_name:
            p_name = p_name.replace('\u202d', '').replace('\u202c', '')
            if not p_name:
                continue
            product_id = product_obj.sudo().search([('default_code', '=', p_name[:3])])
            product_dict[p_name[:3]] = product_id
        _logger.info({
            'product_dict': product_dict
        })
        return product_dict

    def _find_product_id(self, product_type, product_data):
        product_type = product_type.replace('\u202d', '').replace('\u202c', '')
        product_id = product_data.get(product_type[:3], False)
        return product_id if product_id else False

    def _parse_partner_id(self, sheet_data):
        partner_dict = {}
        # partner_name = sheet_data.row_values(4)
        from_partner_name = sheet_data.col_values(2)
        to_partner_name = sheet_data.col_values(10)

        if not from_partner_name and not to_partner_name:
            return False

        partner_name = list(set(from_partner_name[6:] + to_partner_name[6:]))

        partner_obj = self.env['res.partner']

        for p_name in partner_name:
            partner_id = partner_obj.sudo().search([('ref', '=', p_name)])
            partner_dict[p_name] = partner_id

        return partner_dict

    # 查找接车地和目的地
    def _find_from_to_location(self, name, partner_data):
        partner_id = partner_data.get(name, False)
        return partner_id if partner_id else False

    def _find_vin_id(self, vin_code, product_id):
        vin_id = self.env['stock.production.lot'].search([
            ('name', '=', vin_code),
            ('product_id', '=', product_id.id)
        ])
        # TODO： 没有就创建咯？
        #if not vin_id:
        #    vin_id = self.env['stock.production.lot'].create({
        #        'name': vin_code,
        #        'product_id': product_id.id
        #    })
        return vin_id if vin_id else False

    # 解码
    def decoding_string(self, str_word):
        return str_word.replace('\u202d', '').replace('\u202c', '')