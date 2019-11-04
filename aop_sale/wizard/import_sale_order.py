# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.http import request
import logging
import xlrd
from xlrd import xldate_as_tuple
from datetime import datetime
from odoo.exceptions import UserError
import binascii
import traceback

_logger = logging.getLogger(__name__)

CQ_COL = {
    'from_location_id': 3,
    'vin_code': 5,
    'product_id': 6,
    'to_location_id': 9,
    'start_index': 0,
    'file_planned_date': 14,
    'to_station_name': 2
}

CT_COL = {
    'from_location_id': 2,
    'vin_code': 4,
    'product_id': 6,
    'to_location_id': 10,
    'start_index': 6,
    'file_planned_date': 0,
    'to_station_name': 1
}
TWICE_JUMP_TO_NAME_INDEX = 1
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT_YMD = '%Y/%m/%d'


class ImportSaleOrder(models.TransientModel):
    _name = 'import.sale.order.wizard'

    from_location_id = fields.Many2one('res.partner')
    partner_id = fields.Many2one('res.partner', 'Partner')
    file = fields.Binary('File')
    is_transfer = fields.Boolean('Transfer')

    # 读文件
    def _parse_import_file(self):
        data = binascii.a2b_base64(self.file)
        book = xlrd.open_workbook(file_contents=data or b'')
        sheet_data = book.sheet_by_index(0)
        return sheet_data

    # 导入订单
    def start_import_sale_order(self):

        # try:
        #     res = self._import_sale_order()
        # except Exception as exc:
        #     raise UserError(exc.name)

        return self._import_sale_order()

    # 勾选了任务，导入的是CQ
    # 没有勾选，导入CT
    def _import_sale_order(self):
        try:
            sale_order = self.env['sale.order']
            sheet_data = self._parse_import_file()
            order_data = self._parse_order_data()

            if self.is_transfer:
                product_index = CQ_COL.get('product_id')
                start_index = CQ_COL.get('start_index')
                from_partner_index = CQ_COL.get('from_location_id')
                to_partner_index = CQ_COL.get('to_location_id')
                vin_index = CQ_COL.get('vin_code')
                file_planned_date_index = CQ_COL.get('file_planned_date')
                to_station_name_index = CQ_COL.get('to_station_name')
            else:
                product_index = CT_COL.get('product_id')
                start_index = CT_COL.get('start_index')
                from_partner_index = CT_COL.get('from_location_id')
                to_partner_index = CT_COL.get('to_location_id')
                vin_index = CT_COL.get('vin_code')
                file_planned_date_index = CT_COL.get('file_planned_date')
                to_station_name_index = CT_COL.get('to_station_name')

            # 选了 from_location_id 就是二次起跳
            partner_data = self._parse_partner_id(sheet_data, from_location_id=self.from_location_id,
                                                  from_partner_index=from_partner_index,
                                                  to_partner_index=to_partner_index, start_index=start_index)
            product_data = self._parse_product_data(sheet_data, from_location_id=self.from_location_id,
                                                    product_index=product_index, start_index=start_index)

            line_data = self._parse_order_line_data(sheet_data, product_data, partner_data,
                                                    from_location_id=self.from_location_id,
                                                    from_partner_index=from_partner_index,
                                                    to_partner_index=to_partner_index,
                                                    product_index=product_index,
                                                    start_index=start_index,
                                                    vin_index=vin_index,
                                                    file_planned_date_index=file_planned_date_index,
                                                    to_station_name_index=to_station_name_index
                                                    )
            order_data.update({
                'order_line': line_data,
            })
            # _logger.info({
            #     'partner_data': partner_data
            # })
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
            if request and request.debug:
                raise UserError(traceback.format_exc())

            raise UserError(e.name)

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
    def _parse_order_line_data(self, sheet_data, product_data, partner_data, from_location_id=False,
                               from_partner_index=None, to_partner_index=None, product_index=None, start_index=None,
                               vin_index=None, file_planned_date_index=None, to_station_name_index=None):
        line_values = []

        # 选择了 from_location_id, 二次起跳
        if not from_location_id:
            for x in range(start_index, sheet_data.nrows):

                if not sheet_data.cell_value(x, start_index):
                    continue

                product_id = self._find_product_id(sheet_data.cell_value(x, product_index), product_data)
                from_location_id = self._find_from_to_location(sheet_data.cell_value(x, from_partner_index),
                                                               partner_data)
                to_location_id = self._find_from_to_location(sheet_data.cell_value(x, to_partner_index), partner_data)
                if not product_id:
                    continue
                vin_id = self._find_vin_id(sheet_data.cell_value(x, vin_index), product_id, to_location_id=to_location_id)

                try:
                    file_planned_date = datetime(*xldate_as_tuple(sheet_data.cell_value(x, file_planned_date_index), 0)).date()
                except TypeError as e:
                    date_value = sheet_data.cell_value(x, file_planned_date_index).replace('\xa0', '')
                    file_planned_date = datetime.strptime(date_value, DATE_FORMAT_YMD).date()

                line_data = (0, 0, {
                    'product_id': product_id.id,
                    # 'service_product_id': False,
                    'from_location_id': from_location_id.id if from_location_id else False,
                    'to_location_id': to_location_id.id if to_location_id else False,
                    'vin': vin_id.id if vin_id else False,
                    'vin_code': sheet_data.cell_value(x, vin_index),
                    'name': product_id.name,
                    'product_uom_qty': 1,
                    'product_uom': product_id.uom_id.id,
                    'price_unit': 1,
                    'file_planned_date': file_planned_date,
                    'to_station_name': sheet_data.cell_value(x, to_station_name_index),
                    'from_station_name': getattr(from_location_id.city_id, 'name')
                })
                line_values.append(line_data)
        else:
            for x in range(1, sheet_data.nrows):

                product_id = self._find_product_id(sheet_data.cell_value(x, 10), product_data)
                from_location_id = from_location_id
                to_location_id = self._find_from_to_location(sheet_data.cell_value(x, 6), partner_data)

                if not product_id:
                    continue
                vin_id = self._find_vin_id(sheet_data.cell_value(x, 9), product_id, to_location_id=to_location_id)

                file_planned_date_index = 23
                file_planned_date = datetime.strptime(sheet_data.cell_value(x, file_planned_date_index), DATE_FORMAT).date()

                to_station_name = sheet_data.cell_value(x, TWICE_JUMP_TO_NAME_INDEX)
                line_data = (0, 0, {
                    'product_id': product_id.id,
                    # 'service_product_id': False,
                    'from_location_id': from_location_id.id if from_location_id else False,
                    'to_location_id': to_location_id.id if to_location_id else False,
                    'vin': vin_id.id if vin_id else False,
                    'vin_code': sheet_data.cell_value(x, 9),
                    'name': product_id.name,
                    'product_uom_qty': 1,
                    'product_uom': product_id.uom_id.id,
                    'price_unit': 1,
                    'file_planned_date': file_planned_date,
                    'from_station_name': getattr(from_location_id.city_id, 'name'),
                    'to_station_name': to_station_name
                })
                line_values.append(line_data)
        return line_values

    def _parse_product_data(self, sheet_data, from_location_id=False, product_index=None, start_index=None):
        product_dict = {}
        if not from_location_id:

            # partner_name = sheet_data.row_values(4)
            product_name = sheet_data.col_values(product_index)

            if not product_name:
                return False

            product_name = list(set(product_name[start_index:]))

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
        else:
            product_name = sheet_data.col_values(10)

            if not product_name:
                return False

            product_name = list(set(product_name[1:]))

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

    def _parse_partner_id(self, sheet_data, from_location_id=False, from_partner_index=None, to_partner_index=None,
                          start_index=None):
        partner_dict = {}
        if not from_location_id:
            # CQ 和 CT

            # partner_name = sheet_data.row_values(4)
            from_partner_name = sheet_data.col_values(from_partner_index)
            to_partner_name = sheet_data.col_values(to_partner_index)

            if not from_partner_name and not to_partner_name:
                return False

            partner_name = list(set(from_partner_name[start_index:] + to_partner_name[start_index:]))

            partner_obj = self.env['res.partner']

            for p_name in partner_name:
                partner_id = partner_obj.sudo().search([('ref', '=', p_name)])
                partner_dict[p_name] = partner_id

            return partner_dict
        else:
            to_partner_name = sheet_data.col_values(6)

            if not to_partner_name:
                return False

            partner_name = list(set(to_partner_name[1:]))

            partner_obj = self.env['res.partner']

            for p_name in partner_name:
                partner_id = partner_obj.sudo().search([('ref', '=', p_name)])
                partner_dict[p_name] = partner_id

            return partner_dict

    # 查找接车地和目的地
    def _find_from_to_location(self, name, partner_data):
        partner_id = partner_data.get(name, False)
        return partner_id if partner_id else False

    def _find_vin_id(self, vin_code, product_id, to_location_id=False):
        if to_location_id:
            # 如果订单行已经存在该VIN，则不能导入
            res = self.env['sale.order.line'].search([
                ('vin_code', '=', vin_code),
                ('to_location_id', '=', to_location_id.id)
            ])

            # 如果订单已经完成，则可以继续
            res = res.filtered(lambda x: not x.picking_confirm_date)

            # TODO: 过滤交接单号也可以
            # res = res.filtered(lambda x: not x.handover_number)

            if res:
                raise UserError(_('Already exist VIN: {}').format(vin_code))

        vin_id = self.env['stock.production.lot'].search([
            ('name', '=', vin_code),
            ('product_id', '=', product_id.id)
        ])
        return vin_id if vin_id else False

    # 解码
    def decoding_string(self, str_word):
        return str_word.replace('\u202d', '').replace('\u202c', '')
