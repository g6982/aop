# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from xlrd import xldate_as_tuple
from odoo.exceptions import UserError
import binascii
import traceback
from datetime import datetime

_logger = logging.getLogger(__name__)


class ImportDispatchOrder(models.TransientModel):
    _name = 'import.dispatch.order.wizard'

    file = fields.Binary('File')

    # 读文件
    def _parse_import_file(self):
        data = binascii.a2b_base64(self.file)
        book = xlrd.open_workbook(file_contents=data or b'')
        sheet_data = book.sheet_by_index(0)
        return sheet_data

    # 导入订单
    def start_import_purchase_order(self):
        return self._import_purchase_order()

    def _import_purchase_order(self):
        try:
            purchase_order = self.env['purchase.order']
            sheet_data = self._parse_import_file()
            partner_data = self._parse_partner_id(sheet_data)
            product_data = self._parse_product_id(sheet_data)
            picking_type_data = self._parse_picking_type_id(sheet_data)

            order_data = self._parse_order_data(sheet_data, partner_data, product_data, picking_type_data)
            # self._logger_value(sheet_data)

            dispatch_records = purchase_order.with_context({
                'dispatch_order': True
            }).create(order_data)

            _logger.info({
                'dispatch_records': dispatch_records
            })
            view_id = self.env.ref('purchase.purchase_order_tree').id
            form_id = self.env.ref('purchase.purchase_order_form').id

            # 跳转到导入成功后的tree界面
            return {
                'name': 'Dispatch Order',
                'view_type': 'form',
                'view_id': False,
                'views': [(view_id, 'tree'), (form_id, 'form')],
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', dispatch_records.ids)],
                'limit': 80,
                'target': 'current',
            }

            # return {
            #     "type": "ir.actions.do_nothing",
            # }
        except Exception as e:
            self._cr.rollback()
            raise UserError(e)

    def _logger_value(self, sheet_data):
        for x in range(1, sheet_data.nrows - 1):
            for i in range(1, sheet_data.ncols):
                _logger.info({
                    i: sheet_data.cell_value(x, i)
                })

    def _parse_order_data(self, sheet_data, partner_data, product_data, picking_type_data):
        data = []
        for x in range(1, sheet_data.nrows - 1):
            partner_id = partner_data.get(sheet_data.cell_value(x, 3), False)
            picking_type_id = picking_type_data.get(sheet_data.cell_value(x, 10), False)
            product_id = product_data.get(sheet_data.cell_value(x, 6), False)
            date_planned = datetime(*xldate_as_tuple(sheet_data.cell_value(x, 14), 0))

            tmp = {
                'partner_id': partner_id.id if partner_id else False,
                'date_order': date_planned,
                'date_planned': date_planned,
                'user_id': self.env.user.id,
                'dispatch_order': True,
                'picking_type_id': picking_type_id.id if picking_type_id else False,
                'order_line': [(0, 0,
                                {
                                    'product_id': product_id.id if product_id else False,
                                    'name': product_id.name,
                                    'date_planned': date_planned,
                                    'product_qty': 1,
                                    'product_uom': product_id.uom_id.id if product_id else False,
                                    'price_unit': 0
                                }
                                )]
            }
            data.append(tmp)

        return data

    def _parse_partner_id(self, sheet_data):
        partner_dict = {}
        # partner_name = sheet_data.row_values(4)
        partner_name = sheet_data.col_values(3)

        if not partner_name:
            return False

        partner_name = list(set(partner_name[1:]))

        partner_obj = self.env['res.partner']

        for p_name in partner_name:
            partner_id = partner_obj.sudo().search([('name', '=', p_name)])
            partner_dict[p_name] = partner_id

        return partner_dict

    def _parse_product_id(self, sheet_data):
        product_dict = {}
        # partner_name = sheet_data.row_values(4)
        product_name = sheet_data.col_values(6)

        if not product_name:
            return False

        product_name = list(set(product_name[1:]))

        product_obj = self.env['product.product']

        for p_name in product_name:
            product_id = product_obj.sudo().search([('default_code', '=', p_name)])
            product_dict[p_name] = product_id

        return product_dict

    def _parse_picking_type_id(self, sheet_data):
        picking_type_data = {}
        picking_value = sheet_data.col_values(10)
        if not picking_value:
            return False

        picking_value = list(set(picking_value[1:]))

        picking_obj = self.env['stock.picking.type']

        for picking_name in picking_value:
            res = picking_obj.search([
                ('name', '=', u'收货'),
                ('warehouse_id.name', '=', picking_name)
            ])
            picking_type_data[picking_name] = res

        return picking_type_data
