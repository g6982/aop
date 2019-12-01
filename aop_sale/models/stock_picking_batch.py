# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import logging
import time
from itertools import groupby
from odoo.exceptions import UserError
import json
from odoo.tools import config
from ..tools.zeep_client import get_zeep_client_session
from odoo.addons.aop_interface.celery.aop_send_to_wms import send_stock_picking_to_wms
_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # car_no_ids = fields.Many2many('stock.quant.package', string='Loading number')

    un_limit_partner_id = fields.Many2one('res.partner', string='Vendor')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    allow_partner_ids = fields.Many2many('res.partner',
                                         string='Allow partners',
                                         store=True,
                                         compute='_compute_allow_partner_ids')
    limit_state = fields.Selection([
        ('limit', 'Limit'),
        ('un_limit', 'Un-limit')
    ], dafault='un_limit')

    picking_purchase_id = fields.Many2one('purchase.order', 'Purchase', copy=False)

    plan_number = fields.Integer(string='Plan number', default=1)

    vehicle_number = fields.Char(string='Vehicle number')

    mount_car_plan_ids = fields.One2many('mount.car.plan', 'stock_picking_batch_id', string='Mount plan')

    # 定时任务，检查并完成任务
    def complete_stock_picking_batch(self):
        records = self.env['stock.picking.batch'].search([
            '|',
            ('state', '=', 'in_progress'),
            ('picking_purchase_id.state', '!=', 'purchase')
        ])
        for batch_id in records:
            # 装车, 如果所有采购订单行都有值，完成调度订单和采购订单
            if not batch_id.mapped('picking_ids'):
                purchase_line_vin = batch_id.picking_purchase_id.mapped('vin_code')

                # 如果所有vin_code 都有值
                if all(True if x else False for x in purchase_line_vin):
                    batch_id.picking_purchase_id.write({
                        'state': 'purchase'
                    })
                    batch_id.write({
                        'state': 'done'
                    })
                    batch_id.picking_id.batch_id.picking_ids.write({
                        'state': 'done'
                    })
            else:
                picking_state = batch_id.mapped('picking_ids').mapped('state')

                #完成任务
                if all(x == 'done' for x in picking_state):
                    batch_id.picking_purchase_id.write({
                        'state': 'purchase'
                    })
                    batch_id.write({
                        'state': 'done'
                    })

    # 找到来源地的仓库
    def _find_location_warehouse(self, location_id, picking_id=False):
        if picking_id:
            move_line = picking_id.move_lines[0]
            origin_from_location_id = move_line.location_id

            # 针对move 和 picking 不是同一个位置的情况
            if origin_from_location_id.id != location_id.id:

                # 验证： 上级 位置
                if origin_from_location_id.location_id.id == location_id.id:
                    res = self.env['stock.warehouse'].search([
                        ('name', '=', origin_from_location_id.name)
                    ])
                    return res if res else ''

    # 仓库的名字
    def _location_to_warehouse(self, location_id, picking_id=False):

        location_name = location_id.name
        # 如果是总库和子库
        parent_warehouse_id = self.env['stock.warehouse'].search([
            ('name', '=', location_name)
        ])
        parent_location_id = location_id.location_id

        if parent_warehouse_id.parent_id.lot_stock_id.id == parent_location_id.id:
            return location_id.name

        # 仅针对总库, 但是入库到子库
        if picking_id:
            move_line = picking_id.move_lines[0]
            origin_from_location_id = move_line.location_id

            # 针对move 和 picking 不是同一个位置的情况
            if origin_from_location_id.id != location_id.id:

                # 验证： 上级 位置
                if origin_from_location_id.location_id.id == location_id.id:
                    res = self.env['stock.warehouse'].search([
                        ('name', '=', origin_from_location_id.name)
                    ])
                    return res.name if res else ''

        name = location_id.display_name
        name = name.split('/')[0]
        res = self.env['stock.warehouse'].search([
            ('code', '=', name)
        ])
        return res.name if res else ''

    # WMS 任务信息
    def _format_picking_data(self, picking_id):
        '''
        :param picking_id: 任务
        :return: 任务所包含的信息，传送给WMS
        '''
        # 导入的订单。一定存在model。不一定存在颜色
        product_info = picking_id.sale_order_line_id.product_model
        # if not product_info:
        #     product_model = '874'
        #     product_config = 'MJ'
        #     product_name = '19款福克斯'

        picking_type_name = picking_id.picking_type_id.name
        picking_type_name = picking_type_name

        # 也可以使用子位置的数据
        from_location_name = self._location_to_warehouse(picking_id.location_id, picking_id=picking_id)
        to_location_name = self._location_to_warehouse(picking_id.location_dest_id)

        from_warehouse_id = self._find_location_warehouse(picking_id.location_id, picking_id=picking_id)
        # from_location_name = '团结村库'
        # to_location_name = '线边库'

        _logger.info({
            'fields.Datetime.to_string(picking_id.scheduled_date)': fields.Datetime.to_string(picking_id.scheduled_date)
        })
        tmp = {
            'task_id': picking_id.id,
            'product_name': picking_id.sale_order_line_id.product_id.name if picking_id.sale_order_line_id.product_id else '',
            'product_color': picking_id.sale_order_line_id.product_color if picking_id.sale_order_line_id.product_color else '1',
            'product_model': product_info[:3] if product_info else '',
            'product_config': product_info[3:] if product_info else '',
            'supplier_name': self.un_limit_partner_id.name if self.un_limit_partner_id else self.partner_id.name if self.partner_id else '',
            'warehouse_code': from_warehouse_id.code if from_warehouse_id else picking_id.picking_type_id.warehouse_id.code,
            'quantity_done': 1,
            'brand_model_name': picking_id.sale_order_line_id.product_id.brand_id.name if picking_id.sale_order_line_id.product_id.brand_id else '',
            'from_location_id': from_location_name,
            'to_location_id': to_location_name,
            'to_location_type': picking_id.location_dest_id.usage,
            'partner_name': picking_id.partner_id.name,
            'vin': picking_id.vin_id.name if picking_id.vin_id else picking_id.sale_order_line_id.vin.name if picking_id.sale_order_line_id else '',
            'picking_type_name': picking_type_name,
            'batch_id': self.id,
            'scheduled_date': fields.Datetime.to_string(picking_id.scheduled_date)
        }
        return tmp

    # 创建发送列表
    def _create_send_waiting_list(self, waiting_picking_ids):
        res = self.env['send.waiting.list'].sudo().create({
            'partner_id': self.un_limit_partner_id.id if self.un_limit_partner_id else self.partner_id.id if self.partner_id else '',
            'picking_ids': [(6, 0, [picking_id.id for picking_id in waiting_picking_ids])],
            'picking_batch_id': self.id
        })
        return res

    # 接口。创建采购单后，发送任务数据到WMS
    def send_to_wms_data(self):
        data = []
        post_data = []
        assigned_picking_ids = self.picking_ids.filtered(lambda x: x.state == 'assigned')
        waiting_picking_ids = self.picking_ids.filtered(lambda x: x.state != 'assigned')

        waiting_list_id = False
        if waiting_picking_ids:
            waiting_list_id = self._create_send_waiting_list(waiting_picking_ids)

        for picking_id in assigned_picking_ids:
            # 接车并不需要发送到WMS
            if picking_id.picking_incoming_number > 0:
                continue
            tmp = self._format_picking_data(picking_id)
            if waiting_list_id:
                tmp.update({
                    'sequence_id': waiting_list_id.id
                })
            data.append(tmp)

        loading_plan = self.send_vehicle_loading_plan_to_wms()
        if data:
            post_data = {
                'picking_ids': data
            }
        if loading_plan:
            post_data.update({
                'loading_plan': loading_plan
            })
        _logger.info({
            'post_data': post_data
        })
        if post_data:
            task_url = self.env['ir.config_parameter'].sudo().get_param('aop_interface.task_url', False)
            # zeep_task_client = get_zeep_client_session(task_url)

            # 放进 Celery
            send_stock_picking_to_wms.delay(task_url, post_data)
            # 输出中文
            # zeep_task_client.service.sendToTask(json.dumps(post_data, ensure_ascii=False))

    def send_vehicle_loading_plan_to_wms(self):
        data = []
        for line_id in self.mount_car_plan_ids:
            tmp = {
                'transfer_tool_number': line_id.transfer_tool_number,
                'to_location_name': line_id.to_location_id.name if line_id.to_location_id else '',
                'product_model': line_id.name.default_code,
                'product_model_layer': line_id.layer_option,
                'product_model_number': line_id.number,
                'transfer_company_name': self.un_limit_partner_id.name if self.un_limit_partner_id else self.partner_id.name if self.partner_id else '',
            }
            data.append(tmp)
        _logger.info({
            'data': data
        })
        return data

    def limit_warehouse_and_loading_plan(self):
        return self._limit_warehouse_and_loading_plan()

    def _limit_warehouse_and_loading_plan(self):

        if self.picking_ids and self.mount_car_plan_ids:
            warehouse_ids = self.picking_ids.mapped('picking_type_id').mapped('warehouse_id').ids
            warehouse_ids = list(set(warehouse_ids))
            if len(warehouse_ids) > 1 and self.mount_car_plan_ids:
                raise UserError('You must select same warehouse to make loading plan !')
        elif self.picking_ids and not self.mount_car_plan_ids:
            picking_type_ids = self.picking_ids.mapped('picking_type_id')
            limit_state = picking_type_ids.mapped('limit_picking_batch')
            picking_type_name = picking_type_ids.mapped('name')
            picking_type_name = self.format_picking_type_name(picking_type_name)

            # 如果类型做了限制，那么就只能选择同样是被限制了的同种类型的数据，不然抛出提示
            if any(limit_state) and not all(limit_state) and len(picking_type_name) > 1:
                raise UserError('You must select same picking type when you choose [train, road] !')

    # FIXME: 写死了以 ':' 作为分隔
    # 针对公路运输和铁路运输，判断是否是同一种类型
    def format_picking_type_name(self, picking_type_name):
        data = []
        for type_name in picking_type_name:
            tmp = type_name.split(':')
            if len(tmp) != 2:
                continue
            tmp = tmp[1].replace(' ', '')
            data.append(tmp)
        return list(set(data))

    # 生成采购订单，采购：服务产品
    def create_purchase_order(self):
        try:
            self._limit_warehouse_and_loading_plan()
            data, service_product_context = self._get_purchase_data()

            if service_product_context:
                return {
                    'name': _(u'测试'),
                    'view_type': 'form',
                    "view_mode": 'form',
                    'res_model': 'fill.service.product.wizard',
                    'type': 'ir.actions.act_window',
                    'context': service_product_context,
                    'target': 'new',
                }

            # 跨公司创建
            res = self.env['purchase.order'].sudo().create(data)

            # 任务进行中
            self.write({
                'picking_purchase_id': res.id,
                'state': 'in_progress'
            })
        except Exception as e:
            self._cr.rollback()
            import traceback
            raise UserError(traceback.format_exc())

    # 根据条件。获取值
    def get_vendor_id(self):
        if self.limit_state == 'limit' and self.allow_partner_ids:
            return self.partner_id.id if self.partner_id else self.un_limit_partner_id.id
        else:
            return self.un_limit_partner_id.id if self.un_limit_partner_id else self.partner_id.id

    # 跨公司生成采购订单，对应的客户，即是对应公司的客户
    def _get_purchase_data(self):
        vendor = self.get_vendor_id()
        if not vendor:
            raise UserError('You must check selection records.')

        res = {
            'name': str(time.time()),
            'partner_id': vendor,
            'user_id': self.env.user.id,
            'invoice_status': 'no',
            'date_order': fields.Datetime.now(),
            'stock_picking_batch_id': self.id,
            # 'company_id': self._match_company_id(self.partner_id)
            'company_id': self.env.user.company_id.id
        }

        data = self._get_purchase_line_data()
        line_data, lost_service_product_id = data[0], data[-1]

        service_product_context = []
        if lost_service_product_id:
            service_product_context = {
                'default_stock_picking_batch_id': self.id,
                'default_wizard_line_ids': [(0, 0, {
                    'picking_id': line.id,
                    'from_location_id': line.location_id.id,
                    'to_location_id': line.location_dest_id.id
                }) for line in lost_service_product_id],
            }
        res.update({
            'order_line': line_data
        })
        return res, service_product_context

    # 服务产品
    # 产品不能添加公司属性值
    def _get_purchase_line_data(self):
        res = []

        lost_service_product_id = []

        for picking in self.picking_ids:
            for _ in range(picking.picking_incoming_number) if picking.picking_incoming_number > 1 else []:
                res, lost_service_product_id = self._parse_purchase_line_data(picking, lost_service_product_id, res)
            if picking.picking_incoming_number <= 1:
                res, lost_service_product_id = self._parse_purchase_line_data(picking, lost_service_product_id, res)

        return [res, lost_service_product_id]

    def _parse_purchase_line_data(self, picking, lost_service_product_id, res):
        carrier_id = self._parse_service_product_supplier(picking)

        service_product_id = carrier_id.service_product_id if carrier_id else False

        if not service_product_id:
            lost_service_product_id.append(picking)

        for line_id in picking.move_lines:
            data = {
                'product_id': service_product_id.id if service_product_id else line_id.picking_type_id.service_product_id.id if line_id.picking_type_id.service_product_id else False,
                'transfer_product_id': line_id.product_id.id,
                # 'service_product_id': service_product_id.id if service_product_id else False,
                'product_qty': line_id.product_uom_qty,
                'sale_line_id': line_id.sale_order_line_id.id,
                'name': picking.picking_type_id.display_name,
                'date_planned': fields.Datetime.now(),
                'service_contract_price': carrier_id.product_standard_price if carrier_id else 0,
                'price_unit': 0,
                'product_uom': service_product_id.uom_id.id if service_product_id else line_id.picking_type_id.service_product_id.uom_id.id if line_id.picking_type_id.service_product_id else False,
                'batch_stock_picking_id': picking.id,
                'vin_code': line_id.vin_id.name if line_id.vin_id else False,
            }
            res.append((0, 0, data))
        if not picking.move_lines and service_product_id:
            data = {
                'product_id': service_product_id.id,
                'product_qty': 1,
                'name': service_product_id.name,
                'product_uom': service_product_id.uom_id.id,
                'batch_stock_picking_id': picking.id,
                'carrier_id.product_standard_price if carrier_id else ': carrier_id.product_standard_price,
                'price_unit': 0,
                'date_planned': fields.Datetime.now(),
            }
            res.append((0, 0, data))
        lost_service_product_id = list(set(lost_service_product_id))
        return res, lost_service_product_id

    # 查找供应商合同条款
    def _parse_service_product_supplier(self, picking):
        contract_domain = [
            ('supplier_contract_id.partner_id', '=', self.partner_id.id),
            ('from_location_id', '=', picking.location_id.id),
            ('to_location_id', '=', picking.location_dest_id.id)
        ]
        delivery_carrier_id = self.env['delivery.carrier'].search(contract_domain)
        return delivery_carrier_id[0] if delivery_carrier_id else False

    def _match_company_id(self, partner_id):
        res = self.env['res.company'].sudo().search([('code', '=', partner_id.ref)])
        return res.id if res else False

    @api.multi
    @api.depends('picking_ids')
    def _compute_allow_partner_ids(self):
        # self.ensure_one()
        for line in self:
            picking_ids = line.mapped('picking_ids')

            # 搜索客户合同
            customer_contract_id = self.env['customer.aop.contract'].search([
                ('partner_id', 'in', list(set(picking_ids.mapped('partner_id').ids))),
                ('contract_version', '!=', 0)
            ], limit=1)

            # 根据任务和客户和同，过滤供应商合同
            partner_ids = self.find_supplier_contract_partner(picking_ids, customer_contract_id=customer_contract_id)
            if not partner_ids:
                line.allow_partner_ids = False
                line.limit_state = 'un_limit'
            else:
                line.allow_partner_ids = [(6, 0, partner_ids)]
                line.limit_state = 'limit'

    # 任务
    # 判断 来源和目的地 以及步骤
    def find_supplier_contract_partner(self, picking_ids, customer_contract_id=False):
        '''
        :param picking_ids: 任务集
        :param customer_contract_id: 客户合同
        :return: 允许的供应商
        '''
        data = []
        location_ids = picking_ids.mapped('location_id')
        location_dest_ids = picking_ids.mapped('location_dest_id')
        picking_type_ids = picking_ids.mapped('picking_type_id')

        carrier_ids = self.env['delivery.carrier'].search([
            ('from_location_id', 'in', location_ids.ids),
            ('to_location_id', 'in', location_dest_ids.ids),
            ('picking_type_id', 'in', picking_type_ids.ids),
        ])
        picking_set_data = self._parse_from_to_picking_type_ids(picking_ids=picking_ids)

        # 对合同交款，按照供应商合同进行分组， 然后组成条件的集合
        for supplier_contract_id, delivery_carrier_ids in groupby(carrier_ids, lambda x: x.supplier_contract_id):
            carrier_set_data = self._parse_from_to_picking_type_ids(carrier_ids=delivery_carrier_ids)

            if picking_set_data - carrier_set_data:
                continue

            # 如果勾选了允许的客户合同，做一次过滤
            if customer_contract_id and supplier_contract_id.mapped('allow_customer_contract_ids'):
                # 交集
                if not set(customer_contract_id.ids) & set(supplier_contract_id.mapped('allow_customer_contract_ids').ids):
                    continue
            data.append(supplier_contract_id.partner_id.id)

        return data

    # 组成集合
    def _parse_from_to_picking_type_ids(self, picking_ids=False, carrier_ids=False):
        '''
        :param picking_ids: 批量调度选择的任务
        :param carrier_ids: 合同交款
        :return: 条件的集合{(x1,x2,x3), (x4,x5,x6)}
        '''
        data = []
        if carrier_ids:
            for carrier_id in carrier_ids:
                data.append(
                    (carrier_id.from_location_id.id, carrier_id.to_location_id.id, carrier_id.picking_type_id.id)
                )
        elif picking_ids:
            for picking_id in picking_ids:
                data.append(
                    (picking_id.location_id.id, picking_id.location_dest_id.id, picking_id.picking_type_id.id)
                )
        return set(data)

    @api.multi
    def cancel_picking(self):
        # self.mapped('picking_ids').action_cancel()
        picking_state = self.env['ir.config_parameter'].sudo().get_param('aop_interface.enable_cancel_task', False)
        if picking_state:
            self.send_cancel_picking_task_to_wms()
        return self.write({'state': 'cancel'})

    # WMS 任务信息
    def _format_cancel_picking_data(self, picking_id):
        '''
        :param picking_id: 任务
        :return: 取消任务所包含的信息，传送给WMS
        '''
        picking_type_name = picking_id.picking_type_id.name
        picking_type_name = picking_type_name.split(':')[1] if len(
            picking_type_name.split(':')) > 1 else picking_type_name

        tmp = {
            'task_id': picking_id.id,
            'vin': picking_id.sale_order_line_id.vin.name,
            'picking_type_name': picking_type_name,
        }
        return tmp

    @api.multi
    def send_cancel_picking_task_to_wms(self):
        post_data = []
        for line_id in self:
            for picking_id in line_id.picking_ids:
                if picking_id.picking_incoming_number > 0 or not picking_id.sale_order_line_id:
                    continue
                tmp = self._format_cancel_picking_data(picking_id)

                if tmp:
                    post_data.append(tmp)
        if post_data:
            _logger.info({
                'post_data': post_data
            })
            cancel_task_url = self.env['ir.config_parameter'].sudo().get_param('aop_interface.cancel_task_url', False)
            zeep_cancel_task_client = get_zeep_client_session(cancel_task_url)
            # 输出中文
            zeep_cancel_task_client.service.supplier(str(post_data))


class MountCarPlan(models.Model):
    _name = "mount.car.plan"

    name = fields.Many2one('product.product', string='Vehicle model', domain=[('type', '=', 'product')], required=True)

    transfer_tool_number = fields.Char('Transfer tool no', required=True)
    layer_option = fields.Selection([
        ('upper_layer', 'Upper layer'),
        ('lower_layer', 'Lower layer')
    ], string='Layer', required=True)

    stock_picking_batch_id = fields.Many2one('stock.picking.batch', 'Dispatch order')

    to_location_id = fields.Many2one('stock.location', 'To location')

    number = fields.Integer('Number', required=True)
