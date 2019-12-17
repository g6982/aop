# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import time
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    @api.depends('from_location_id', 'to_location_id')
    def _compute_allowed_carrier_ids(self):
        for order_line in self:
            if order_line.from_location_id and order_line.to_location_id:
                from_location_id = self._transfer_district_to_location(order_line.from_location_id)
                to_location_id = self._transfer_district_to_location(order_line.to_location_id)
                search_domain = [
                    ('customer_contract_id', '=', order_line.customer_contract_id.id),
                    ('from_location_id', '=', from_location_id.id),
                    ('to_location_id', '=', to_location_id.id)
                ]
                delivery_id = self.env['delivery.carrier'].search(search_domain)

                order_line.allowed_carrier_ids = [(6, 0, delivery_id.ids)]

    vin = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    service_product_id = fields.Many2one('product.product',
                                         string='Product',
                                         domain=[('sale_ok', '=', True)],
                                         ondelete='restrict',
                                         related='delivery_carrier_id.service_product_id',
                                         readonly=True
                                         )
    from_location_id = fields.Many2one('res.partner', 'From location')
    to_location_id = fields.Many2one('res.partner', 'To location')
    delivery_count = fields.Integer('Count', related='order_id.delivery_count')

    handover_number = fields.Char('Handover number')

    contract_id = fields.Many2one('aop.contract', 'Contract')
    customer_contract_id = fields.Many2one('customer.aop.contract', 'Contract')

    delivery_carrier_id = fields.Many2one(
        'delivery.carrier',
        'Delivery carrier'
    )

    vin_code = fields.Char('VIN Code')

    # 部分完成的情况
    state = fields.Selection(selection_add=[('part_done', 'Part done')])

    # 针对单条订单行，也能创建stock,picking，而不影响整个的状态
    stock_picking_state = fields.Boolean('Picking state', compute='_compute_stock_picking_state', copy=False)
    stock_picking_ids = fields.Many2many('stock.picking', string='Pickings', copy=False)

    allowed_carrier_ids = fields.Many2many(
        'delivery.carrier',
        copy=False,
        compute='_compute_allowed_carrier_ids',
        store=True
    )

    replenish_picking_id = fields.Many2one('stock.picking', copy=False)

    allowed_vin_ids = fields.Many2many('stock.production.lot', copy=False)

    file_validate = fields.Binary('file')

    current_picking_id = fields.Many2one('stock.picking', 'Current picking task', compute='_compute_current_picking_id', store=True)
    current_picking_type_id = fields.Many2one('stock.picking.type', related='current_picking_id.picking_type_id')
    picking_confirm_date = fields.Datetime('Confirm date', compute='_compute_current_picking_id', inverse='_set_picking_confirm_date', store=True)

    file_planned_date = fields.Date('Imported date')

    route_id = fields.Many2one('stock.location.route',
                               string='Route',
                               related='delivery_carrier_id.route_id',
                               store=True,
                               readonly=True
                               )

    write_date = fields.Datetime('Last Updated on', index=True, readonly=False)

    from_station_name = fields.Char('From')
    to_station_name = fields.Char('To')

    product_color = fields.Char('Product color')
    product_model = fields.Char('Product model')

    created_by_picking_id = fields.Many2one('stock.picking', 'Created by picking')

    @api.multi
    @api.depends('stock_picking_ids', 'stock_picking_ids.state', 'stock_picking_ids.date_done')
    def _compute_current_picking_id(self):
        for line in self:
            if not line.stock_picking_ids:
                continue

            current_picking_id = line.stock_picking_ids.filtered(lambda x: x.state == 'assigned')

            if not current_picking_id:
                current_picking_id = line.stock_picking_ids.sorted('id')[-1]

            line.current_picking_id = current_picking_id.id

            if current_picking_id.state == 'done' and current_picking_id.id == line.stock_picking_ids.sorted('id')[-1].id:
                line.picking_confirm_date = current_picking_id.date_done

    def _set_picking_confirm_date(self):
        pass

    def replenish_stock_picking_order(self):
        try:
            for line in self:
                if not line.vin_code or line.vin or not line.order_id or line.replenish_picking_id:
                    continue
                # _logger.info({
                #     'vin_code': line.vin_code,
                #     'vin': line.vin,
                #     'replenish_picking_id': line.replenish_picking_id
                # })
                line.create_stock_picking_in_stock()
        except Exception as e:
            self._cr.rollback()
            raise UserError(e)

    @api.multi
    def create_stock_picking_in_stock(self):
        return self._parse_stock_in_picking_data()

    # FIXME: 使用中文搜索？ serious ???!
    def get_stock_picking_type_id(self, location_id):
        res = self.env['stock.picking.type'].search([
            ('name', '=', u'接车')
        ], limit=1)

        return res[0] if res else False

    def get_vin_id_in_stock(self):
        vin_obj = self.env['stock.production.lot']

        vin_id = vin_obj.search([
            ('name', '=', self.vin_code),
            ('product_id', '=', self.product_id.id)
        ])
        # if not vin_id:
        #     vin_id = vin_obj.create({
        #         'name': self.vin_code,
        #         'product_id': self.product_id.id if self.product_id else False
        #     })
        return vin_id.id if vin_id else False

    @api.multi
    def _parse_stock_in_picking_data(self):
        for line in self:
            partner_id = line.order_id.partner_id
            to_location_id = line._transfer_district_to_location(line.from_location_id)
            picking_type_id = line.get_stock_picking_type_id(to_location_id)
            product_id = line.product_id
            vin_id = line.get_vin_id_in_stock()
            picking_obj = self.env['stock.picking']
            data = {
                'date': line.create_date,
                'partner_id': partner_id.id,
                'location_id': partner_id.property_stock_supplier.id if partner_id else False,
                'location_dest_id': to_location_id.id,
                'picking_type_id': picking_type_id.id if picking_type_id else False,
                'scheduled_date': line.create_date,
                'picking_type_code': 'incoming',
            }

            picking_id = picking_obj.create(data)

            line.replenish_picking_id = picking_id.id
            move_data = {
                'name': product_id.name + '/income' + str(time.time()),
                'product_id': product_id.id if product_id else False,
                'product_uom_qty': 1,
                'product_uom': product_id.uom_id.id if product_id else False,
                'location_id': partner_id.property_stock_supplier.id if partner_id else False,
                'location_dest_id': picking_type_id.default_location_dest_id.id if picking_type_id else False,
                'state': 'draft',
                'picking_id': picking_id.id,
                'picking_type_id': picking_type_id.id if picking_type_id else False,
                'service_product_id': picking_type_id.service_product_id.id if picking_type_id.service_product_id else False,
                'procure_method': 'make_to_stock',
                'picking_code': 'incoming',
                'vin_id': vin_id.id,
            }
            move_id = self.env['stock.move'].create(move_data)

            move_id = move_id.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
            move_id._action_assign()

            # 填充VIN
            picking_id.move_line_ids.lot_id = vin_id.id
            picking_id.move_line_ids.qty_done = 1
            picking_id.move_line_ids.lot_name = vin_id.name

            # picking_id.button_validate()

            # _logger.info({
            #     'picking_id': picking_id,
            #     'state': picking_id.state
            # })

    @api.onchange('stock_picking_ids')
    def _compute_stock_picking_state(self):
        for line in self:
            if not line.stock_picking_ids:
                line.stock_picking_state = False
            else:
                picking_state = line.stock_picking_ids.filtered(lambda x: x.state not in ['cancel'])
                # _logger.info({
                #     'picking_state': picking_state
                # })
                if picking_state:
                    line.stock_picking_state = True
                else:
                    line.stock_picking_state = False

    # 获取截断？或者全量的时延
    def _get_current_stock_route_delay(self):
        all_rules = self.route_id.mapped('rule_ids')
        if not all_rules:
            return self.route_id.sum_delay
        all_src_location_ids = all_rules.mapped('location_src_id')

        # 找到库存的位置
        res = self.env['stock.quant'].search([
            ('lot_id', '=', self.vin.id),
            ('location_id', 'in', all_src_location_ids.ids),
            ('quantity', '=', 1)
        ])
        res = res.sorted(lambda x: x.id)
        return sum(x.delay for x in all_rules[all_src_location_ids.ids.index(res[-1].location_id.id):]) if res else self.route_id.sum_delay

    # 新增 服务产品
    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id)

        sum_delay = self._get_current_stock_route_delay()
        # date_planned = 订单的确认日期 + 订单行的交货提前时间 - 路由标准实效 + 公司的security_lead + 规则的 delay
        date_planned = self.order_id.confirmation_date \
            + timedelta(days=self.customer_lead or 0.0) \
            + timedelta(sum_delay) \
            + timedelta(days=self.order_id.company_id.security_lead)

        res.update({
            'service_product_id': self.service_product_id.id,
            'vin_id': self.vin.id,
            'delivery_carrier_id': self.delivery_carrier_id.id,
            'delivery_to_partner_id': self.to_location_id.id,
            'sale_order_line_id': self.id,
            'date_planned': date_planned
        })
        return res

    @api.multi
    def name_get(self):
        result = []
        for so_line in self.sudo():
            name = '%s - %s - %s' % (
                so_line.order_id.name,
                so_line.name.split('\n')[0] if so_line.name else [] or so_line.product_id.name,
                so_line.id if so_line else ''
            )
            if so_line.order_partner_id.ref:
                name = '%s (%s)' % (name, so_line.order_partner_id.ref)
            result.append((so_line.id, name))
        return result

    def action_confirm_sale_order(self):
        return self.order_id.action_confirm() if self.order_id else False

    def action_view_delivery(self):
        return self.order_id.action_view_delivery() if self.order_id else False

    # 不做检查
    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        pass

    # 检查限制
    @api.onchange('product_id', 'route_id', 'service_product_id')
    def _onchange_domain_service_product_route(self):
        pass

    # 获取真实的路由的终点
    def _get_real_location_id(self, carrier_id):
        all_rules = carrier_id.route_id.rule_ids

        # 路由一般来说，存在规则的
        if not all_rules:
            return carrier_id.location_id

        # 获取最后一条规则
        last_rules = all_rules[-1]
        real_location_id = last_rules.location_id
        return real_location_id

    @api.multi
    def _action_launch_stock_rule(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        errors = []
        for line in self:
            line._compute_stock_picking_state()

            if line.stock_picking_state or not line.vin:
                continue

            # if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
            if line.state not in ['sale', 'part_done'] or not line.product_id.type in ('consu', 'product'):
                continue
            qty = line._get_qty_procurement()
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line.order_id.procurement_group_id
            if not group_id:
                group_id = self.env['procurement.group'].create({
                    'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
                    'sale_id': line.order_id.id,
                    'partner_id': line.order_id.partner_shipping_id.id,
                })
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty

            procurement_uom = line.product_uom
            quant_uom = line.product_id.uom_id

            get_param = self.env['ir.config_parameter'].sudo().get_param
            if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                product_qty = line.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
                procurement_uom = quant_uom

            try:

                to_location_id = self._get_real_location_id(line.delivery_carrier_id)

                self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom,
                                                  to_location_id,
                                                  line.name,
                                                  line.order_id.name, values)
            except UserError as error:
                # raise UserError(error)
                # return False
                errors.append(error.name)
        if errors:
            raise UserError('\n'.join(errors))
        return True

    def _transfer_district_to_location(self, partner_id):
        # location_obj = self.env['stock.location']
        # filter_domain = []
        # if partner_id.district_id if hasattr(partner_id, 'district_id') else False:
        #     filter_domain = [('name', '=', partner_id.district_id.name)]
        # elif partner_id.city_id if hasattr(partner_id, 'city_id') else False:
        #     filter_domain = [('name', '=', partner_id.city_id.name)]
        #
        # if not filter_domain:
        #     filter_domain = [('name', '=', partner_id.name)]
        #
        # location_id = None
        # if filter_domain:
        #     location_id = location_obj.search(filter_domain)
        #
        # if not location_id:
        #     # 保留取上级的默认客户位置
        #     location_id = partner_id.parent_id.property_stock_customer
        # return location_id
        return partner_id.property_stock_customer

    # 先把订单的vin 填写
    def _fill_order_line_vin_id(self):
        for line in self:
            line.vin = line.get_vin_id_in_stock()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection([('dispatch', 'Dispatch'), ('customer', 'Customer')], store=True,
                                  compute='_get_order_type')
    from_location_id = fields.Many2one('res.partner', 'From location')

    # 部分完成的情况
    state = fields.Selection(selection_add=[('part_done', 'Part done')])

    write_off_state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft', string='Write off state')

    delivery_company_id = fields.Many2one('res.company', 'Delivery company')

    # 检查月结
    @api.constrains('partner_id')
    def _check_monthly_state(self):
        period_obj = self.env['account.period']
        search_domain = False
        if self.create_date:
            search_domain = [
                ('date_start', '<=', self.create_date),
                ('date_stop', '>=', self.create_date),
                ('monthly_state', '=', True)
            ]
        elif self.date_order:
            search_domain = [
                ('date_start', '<=', self.date_order),
                ('date_stop', '>=', self.date_order),
                ('monthly_state', '=', True)
            ]
        if search_domain:
            if period_obj.search(search_domain):
                raise UserError(_('Has been monthly!'))

    # 核销的数据
    def _get_write_off_context(self):
        order_lines = self.order_line

        res = []
        for x in order_lines:
            res.append(
                (0, 0, {
                    'sale_order_line_id': x.id
                })
            )
        return {
            'default_write_off_line_ids': res
        }

    def write_off_order_line(self):
        context_write_off = self._get_write_off_context()
        return {
            'name': _('Write-off'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'write.off.line.wizard',
            'type': 'ir.actions.act_window',
            'context': context_write_off,
            'target': 'new',
        }

    @api.depends('partner_id')
    def _get_order_type(self):
        for order in self:
            if self._context.get('order_type_context', False):
                order.order_type = 'dispatch'
            else:
                order.order_type = 'customer'

    # 获取合同
    def _fetch_customer_contract(self, res):
        res = self.env['customer.aop.contract'].search([
            ('partner_id', '=', res.partner_id.id),
            ('contract_version', '!=', 0),
            ('date_start', '<', res.create_date),
            ('date_end', '>', res.create_date)
        ])

        # 获取到多个合同
        return res if res else False

    def _transfer_district_to_location(self, partner_id):
        return partner_id.property_stock_customer

    # 尝试获取条款
    def _get_contract_line(self, contract_ids, from_location_id, to_location_id, order_line):
        product_id = order_line.product_id
        product_color = order_line.product_color
        delivery_ids = []
        for contract_id in contract_ids:
            if delivery_ids:
                continue

            # 先把位置相同的筛选出来
            carrier_ids = contract_id.mapped('delivery_carrier_ids').filtered(
                lambda x:
                x.from_location_id.id == from_location_id.id and
                x.to_location_id.id == to_location_id.id
            )
            if not carrier_ids:
                continue

            # 初始化变量
            color_contract_line_ids = False

            # 过滤产品
            product_contract_line_ids = carrier_ids.filtered(lambda x: x.product_id.id == product_id.id)

            # 找到了产品, 找颜色
            if product_contract_line_ids and product_color:
                color_contract_line_ids = product_contract_line_ids.filtered(lambda x: x.product_color == product_color)

            # 找到了颜色
            if color_contract_line_ids:
                carrier_ids = color_contract_line_ids

            # 找到了货物，没有找到颜色
            if product_contract_line_ids and not color_contract_line_ids:
                carrier_ids = product_contract_line_ids

            # 没有找到货物
            if not product_contract_line_ids:
                no_product_carrier_ids = carrier_ids.filtered(lambda x: not x.product_id)
                if no_product_carrier_ids:
                    carrier_ids = no_product_carrier_ids

            # 可能存在多条这样的记录
            for line_id in carrier_ids:
                line_id = line_id if not line_id.goto_delivery_carrier_id else line_id.goto_delivery_carrier_id
                delivery_ids.append(line_id)

        # 没有就抛出异常
        if not delivery_ids:
            raise ValueError('Can not find correct delivery carrier !')

        delivery_ids = list(set(delivery_ids))

        return delivery_ids

    # 查找 条款
    def _find_contract_line(self, contract_ids, order_line):

        order_from_location_id = self._transfer_district_to_location(order_line.from_location_id)
        order_to_location_id = self._transfer_district_to_location(order_line.to_location_id)

        delivery_ids = self._get_contract_line(contract_ids, order_from_location_id, order_to_location_id, order_line)

        return delivery_ids

    # 针对导入，根据货物，选择出对应的服务产品和路由，如果路由存在多个，默认选择第一条
    def _find_service_product(self, contract_line):
        return contract_line[0].service_product_id if contract_line else False

    # 过滤
    def _find_service_product_ids(self, contract_line):
        return [line.mapped('service_product_id').id for line in contract_line if
                line.mapped('service_product_id')] if contract_line else False

    # TODO: 废弃
    # 路线的选择，使用开始位置和结束位置，多条，自己选择
    # 使用位置，每一个客户，对应一个默认的仓库的位置
    def _find_route_id(self, res, line_id):
        # 获取源地址和目的地址
        # from_location_id = res.from_location_id.property_stock_customer
        # to_location_id = res.partner_id.property_stock_customer

        # sale order line 的from 和 to
        # TODO: 需要确认，是否使用默认的地址
        # from 使用第二级
        # to 使用第二级
        from_location_id = line_id.from_location_id.parent_id.property_stock_customer
        to_location_id = line_id.to_location_id.parent_id.property_stock_customer

        if not from_location_id or not to_location_id:
            return False

        rule_ids = self.env['stock.rule'].search([
            '|',
            ('location_src_id', '=', from_location_id.id),
            ('location_id', '=', to_location_id.id)
        ])

        res = self.env['stock.location.route'].search([
            ('rule_ids', 'in', rule_ids.ids)
        ])

        route_id = [
            route_line for route_line in res if (route_line.rule_ids[0].location_src_id.id == from_location_id.id and
                                                 route_line.rule_ids[-1].location_id.id == to_location_id.id)]

        return route_id[0] if route_id else False

    # 根据合同条款，查找路由
    def _find_contract_route_id(self, contract_line):
        return contract_line[0].route_id if contract_line else False

    # 过滤
    def _find_contract_route_ids(self, contract_line):
        return [line.mapped('route_id').id for line in contract_line if
                line.mapped('route_id')] if contract_line else False

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)

        # 获取合同
        # 返回 该用户的多个合同
        contract_ids = self._fetch_customer_contract(res)
        if not contract_ids:
            return res

        # 接车单创建
        # res.order_line.replenish_stock_picking_order()

        data = []
        for line_id in res.order_line:
            # 获取数据
            # 如果 delivery_carrier_id 存在多条条款，需要用户进行选择
            # 默认使用第一条
            delivery_carrier_id = self._find_contract_line(contract_ids, line_id)
            service_product_id = self._find_service_product(delivery_carrier_id)
            route_id = self._find_contract_route_id(delivery_carrier_id)

            allowed_carrier_ids = [x.id for x in delivery_carrier_id]
            tmp = {
                    'service_product_id': service_product_id.id if service_product_id else False,
                    'route_id': route_id.id if route_id else False,
                    'price_unit': delivery_carrier_id[0].fixed_price if delivery_carrier_id else 0,
                    'delivery_carrier_id': delivery_carrier_id[0].id if delivery_carrier_id else False,
                    'customer_contract_id': delivery_carrier_id[0].customer_contract_id.id if delivery_carrier_id else False,
                    'allowed_carrier_ids': [(6, 0, allowed_carrier_ids)] if allowed_carrier_ids else False
                }
            if not line_id.vin:
                tmp['vin'] = self.get_vin_id_stock(line_id)

            data.append(
                (1, line_id.id, tmp)
            )

        if data:
            res.write({
                'order_line': data
            })

            res.order_line._compute_amount()

        return res

    @api.multi
    def write(self, vals):
        for line in self:
            line._check_monthly_state()
        return super(SaleOrder, self).write(vals)
    
    def get_vin_id_stock(self, line_id):
        res = self.env['stock.production.lot'].search([
            ('name', '=', line_id.vin_code),
            ('product_id', '=', line_id.product_id.id)
        ])
        if len(res) > 1:
            raise UserError('More than one record.')
        return res.id if res else False

    # 拆分订单，如果定义了 delivery_company_id 才需要进行？或者在公司上进行配置
    # 中集可能只需要做一段任务，不需要做两端，需要根据合同？来判断，哪一段需要做
    # 特货公司？ 很对路由 A -> X -> Y -> B( -> M -> N -> C)
    # A-X
    # X-Y
    # Y-B
    # 假定只有三段的情况，这里允许多段
    # X-Y 段，由特货执行，保存订单即可
    # A-X / Y-B 由中集执行
    def split_sale_order_to_delivery_company(self):
        res = []
        for line in self:
            for order_line_id in line.order_line:
                # 对于订单，针对每一行
                if not order_line_id.route_id:
                    continue
                # 判断是否存在站点
                if any(order_line_id.route_id.sudo().mapped('rule_ids').mapped('is_station_line')):
                    # 去除是站点的，剩下的都是正常的线段
                    rule_area = order_line_id.route_id.sudo().mapped('rule_ids').filtered(lambda x: not x.is_station_line)
                    rule_area = self.split_filter_rule_area(rule_area, order_line_id)

                    # 站点不需要中集做，但是需要体现出来
                    disallow_area = order_line_id.route_id.sudo().mapped('rule_ids').filtered(lambda x: x.is_station_line)

                    for disallow_id in disallow_area:
                        disallow_data = self.split_to_create_order_value(disallow_id, order_line_id,
                                                                         line.company_id, lock=False)
                        res.append(disallow_data)

                    # 规则分段的时候
                    # FIXME: 订单需要关联么？
                    for rule_id in rule_area:
                        tmp = self.split_to_create_order_value(rule_id, order_line_id, line.delivery_company_id)
                        res.append(tmp)
        if res:
            result = self.env['sale.order'].sudo().create(res)
            _logger.info({
                'result': result
            })

    # 根据合同，筛选出需要运送的线段
    def split_filter_rule_area(self, rule_area, order_line_id):
        allow_area = []
        for rule_id in rule_area:
            contract_state = self.split_filter_rule_contract(rule_id, order_line_id)
            # _logger.info({
            #     'from': rule_id.location_src_id.display_name,
            #     'to': rule_id.location_id.display_name,
            #     'contract_state': contract_state
            # })
            if contract_state:
                allow_area.append(rule_id)
        return allow_area

    # 针对订单里面的客户
    # 找到该规则是否存在合同
    def split_filter_rule_contract(self, rule, order_line_id):
        domain_filter = [
            ('from_location_id', '=', rule.location_src_id.id),
            ('to_location_id', '=', rule.location_id.id),
            ('customer_contract_id.partner_id', '=', order_line_id.order_id.partner_id.id)
        ]
        res = self.env['delivery.carrier'].search(domain_filter)
        return True if res else False

    # 返回订单头
    def split_order_header(self, order_line_id, company_id, lock=False):
        order_value = {
            'partner_id': order_line_id.order_id.partner_id.id,
            'partner_invoice_id': order_line_id.order_id.partner_id.id,
            'partner_shipping_id': order_line_id.order_id.partner_id.id,
            'company_id': company_id.id
        }

        # 特货公司创建的订单，需要锁定
        if lock:
            order_value.update({
                'state': 'done'
            })
        return order_value

    # 订单行
    def split_order_line_value(self, order_line_id):
        res = {
            'product_id': order_line_id.product_id.id,
            'vin': order_line_id.vin.id if order_line_id.vin else False,
            'vin_code': order_line_id.vin_code,
            'name': order_line_id.product_id.name,
            'product_uom_qty': 1,
            'product_uom': order_line_id.product_id.uom_id.id,
            'price_unit': 1,
            'file_planned_date': order_line_id.file_planned_date,
            'to_station_name': order_line_id.to_station_name,
            'from_station_name': order_line_id.from_station_name
        }
        return res

    def split_order_line_location_partner(self, rule):
        from_location_id = rule.location_src_id
        to_location_id = rule.location_id
        partner_obj = self.env['res.partner'].sudo()
        from_location_partner = partner_obj.search([
            ('property_stock_customer', '=', from_location_id.id)
        ])
        to_location_partner = partner_obj.search([
            ('property_stock_customer', '=', to_location_id.id)
        ])

        return from_location_partner[0], to_location_partner[0]

    # 根据规则创建订单
    # 针对一段规则
    def split_to_create_order_value(self, rule_id, order_line_id, company_id, lock=False):
        order_value = self.split_order_header(order_line_id, company_id, lock=lock)
        order_line_value = self.split_order_line_value(order_line_id)

        from_partner_id, to_partner_id = self.split_order_line_location_partner(rule_id)

        order_line_value.update({
            'from_location_id': from_partner_id.id,
            'to_location_id': to_partner_id.id
        })
        order_value.update({
            'order_line': [(0, 0, order_line_value)]
        })
        return order_value

    @api.multi
    def action_confirm(self):
        # 如果指定了，就需要去执行
        if any(self.mapped('delivery_company_id')):
            return self.split_sale_order_to_delivery_company()

        # # 先去填充一次VIN
        for order in self:
            order_line_ids = order.order_line
            for line_id in order_line_ids:
                if line_id.vin:
                    continue
                line_id._fill_order_line_vin_id()

        # 判断。如果判断的结果是存在VIN不在路由上的。则先进行调度
        if self.dispatch_or_not():
            return self.change_vin_location_to_route()

        # 如果一个VIN都没有。不运行
        vin_order_ids = self.mapped('order_line').filtered(lambda x: not x.vin)

        # 全部都没VIN
        if len(self.mapped('order_line')) == len(vin_order_ids):
            raise UserError(_('Please wait until the VIN in stock. Any question, Contact administrator. '))

        # if not any([True if line.mapped('vin') else False for line in self.order_line]):
        #     raise UserError(_('You can not make order until the product have vin or stock.'))
        res = super(SaleOrder, self).action_confirm()

        # FIXME: 补丁
        self.picking_ids.filtered(
            lambda picking: picking.state == 'confirmed').action_assign() if self.picking_ids.filtered(
            lambda picking: picking.state == 'confirmed') and not self.picking_ids.filtered(
            lambda picking: picking.state == 'assigned') else False

        for order in self:
            order.mapped('order_line')._compute_stock_picking_state()

            # 存在完成，且部分未完成，才写入部分完成的状态
            if order.mapped('order_line').filtered(lambda x: x.stock_picking_state) and order.mapped('order_line').filtered(lambda x: not x.stock_picking_state):
                order.write({
                    'state': 'part_done',
                    'confirmation_date': fields.Datetime.now()
                })

            # PATCH: 生成后，完善上下级位置，自动填充
            self.patch_sale_order_picking_assign_picking(order)
        return res

    # 取消的同时。删除
    @api.multi
    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()

        self.mapped('picking_ids').unlink()
        return res

    @api.multi
    def action_done(self):
        if all(self.mapped('order_line').mapped('stock_picking_state')):
            return super(SaleOrder, self).action_done()
        else:
            return self.write({'state': 'part_done'})

    @api.multi
    def update_stock_picking(self):
        for order in self:
            order_line_ids = order.order_line.filtered(lambda x: not x.stock_picking_state)
            if order_line_ids:
                order_line_ids._fill_order_line_vin_id()
                order_line_ids._action_launch_stock_rule()

            # 更新任务的时候，也使用
            self.patch_sale_order_picking_assign_picking(order)
            order_line_ids._compute_stock_picking_state()
            if all(order.order_line.mapped('stock_picking_state')):
                order.write({
                    'state': 'sale'
                })

    def change_vin_location_to_route(self):
        context_write_off = {
            'default_sale_order_id': self.id
        }
        return {
            'name': _('Dispatch'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'stock.location.to.route.location.wizard',
            'type': 'ir.actions.act_window',
            'context': context_write_off,
            'target': 'new',
        }

    @api.multi
    def dispatch_or_not(self):
        # 在手数大于0 (=1)
        # 预留为0
        stock_quant_ids = self.env['stock.quant'].search([
            ('quantity', '=', 1),
            ('reserved_quantity', '=', 0)
        ])
        for order in self:
            for line in order.order_line:
                if not line.vin or line.replenish_picking_id:
                    continue

                from_location_id = self._transfer_district_to_location(line.from_location_id)
                stock_location_id = stock_quant_ids.filtered(lambda x: x.lot_id.id == line.vin.id)

                stock_location_id = stock_location_id.sorted(lambda x: x.id)[-1] if stock_location_id else stock_location_id

                route_location_ids = line.route_id.rule_ids.mapped('location_src_id').ids

                if from_location_id.id != stock_location_id.location_id.id and stock_location_id.location_id.id not in route_location_ids:
                    # 库存的上级位置
                    if stock_location_id.location_id.location_id.id not in route_location_ids if stock_location_id.location_id.location_id else False:
                        return True
        return False

    def link_new_picking_and_by_picking(self, new_picking_id, created_by_picking_id):
        '''
        :param new_picking_id: 生成的任务
        :param created_by_picking_id: 由该任务生成的订单
        :return:
        '''
        last_picking_move_id = new_picking_id.move_lines
        last_picking_move_id = last_picking_move_id[0]

        created_picking_move_id = created_by_picking_id.move_lines
        created_picking_move_id = created_picking_move_id[0]

        # 对新生成的任务，以及由此生成的任务，进行关联
        last_picking_move_id.move_dest_ids = [(4, created_picking_move_id.id)]
        created_picking_move_id.move_orig_ids = [(4, last_picking_move_id.id)]

    # 截断的生成任务后，路由设置到总库，出库的时候，判断是否使用子库的库存
    # 阶段后，如果存在 created_by_picking_id， 则需要进行关联
    def patch_sale_order_picking_assign_picking(self, order):
        '''
        :param order: 订单
        :return:
        '''
        for line_id in order.order_line:

            if not line_id.stock_picking_ids:
                continue

            # 获取到最后一条记录，只需要处理，状态 state == 'waiting'
            # 排序，取最后一条记录
            last_picking_id = line_id.stock_picking_ids.sorted(lambda x: x.id)[-1]

            # 对任务进行关联
            if line_id.created_by_picking_id:
                # 关联任务
                self.link_new_picking_and_by_picking(last_picking_id, line_id.created_by_picking_id)

            first_picking_id = line_id.stock_picking_ids.sorted(lambda x: x.id)[0]

            if first_picking_id.state != 'waiting':
                continue

            # 使用子位置的库存信息
            # 有且仅有一条记录
            stock_move = first_picking_id.move_lines

            if len(stock_move) != 1:
                continue

            from_location_id = stock_move.location_id
            vin_id = stock_move.vin_id

            # from_location_id 如果存在下级，则可以使用下级的数据
            stock_quant_ids = vin_id.quant_ids

            if not stock_quant_ids:
                continue

            stock_quant_id = stock_quant_ids.filtered(lambda x: x.quantity == 1)

            real_stock_location = stock_quant_id.location_id

            # 如果真实的库存位置，是路由的总库位置的子位置，则可以进行出库，替换from_location，重新检查库存
            partner_location_id = real_stock_location.location_id

            if not partner_location_id:
                continue

            if from_location_id.id == partner_location_id.id:
                stock_move.write({
                    'location_id': real_stock_location.id,
                    'procure_method': 'make_to_stock'
                })
            # 检查预留
            first_picking_id.write({
                'real_stock_location_id': real_stock_location.id
            })
            first_picking_id.action_assign()
