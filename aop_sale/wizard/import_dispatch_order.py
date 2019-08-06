# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import xlrd
from odoo.exceptions import UserError
import binascii
import traceback
import re

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
            order_data = self._parse_order_data(sheet_data, partner_data)
            # self._logger_value(sheet_data)

            return {
                "type": "ir.actions.do_nothing",
            }
        except Exception as e:
            raise UserError(e)

    def _logger_value(self, sheet_data):
        for x in range(1, sheet_data.nrows - 1):
            for i in range(1, sheet_data.ncols):
                _logger.info({
                    i: sheet_data.cell_value(x, i)
                })

    def _parse_order_data(self, sheet_data, partner_data):
        data = []
        for _ in sheet_data:
            pass

    def _parse_partner_id(self, sheet_data):
        partner_dict = {}
        # partner_name = sheet_data.row_values(4)
        partner_name = sheet_data.col_values(4)

        if not partner_name:
            return False

        partner_name = list(set(partner_name[1:]))

        partner_obj = self.env['res.partner']

        for p_name in partner_name:
            partner_id = partner_obj.sudo().search([('name', '=', p_name)])
            partner_dict[p_name] = partner_id

        _logger.info(partner_dict)
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
            product_id = product_obj.sudo().search([('name', '=', p_name)])
            product_dict[p_name] = product_id

        _logger.info(product_dict)
        return product_dict
