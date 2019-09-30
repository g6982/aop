# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
import time


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

    # allowed_route_ids = fields.Many2many('stock.location.route', copy=False)
    # allowed_service_product_ids = fields.Many2many('product.product', domain=[('sale_ok', '=', True)], copy=False)
    allowed_carrier_ids = fields.Many2many('delivery.carrier', copy=False)

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
                _logger.info({
                    'vin_code': line.vin_code,
                    'vin': line.vin,
                    'replenish_picking_id': line.replenish_picking_id
                })
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
                _logger.info({
                    'picking_state': picking_state
                })
                if picking_state:
                    line.stock_picking_state = True
                else:
                    line.stock_picking_state = False



    # 新增 服务产品
    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        res.update({
            'service_product_id': self.service_product_id.id,
            'vin_id': self.vin.id,
            'delivery_carrier_id': self.delivery_carrier_id.id,
            'delivery_to_partner_id': self.to_location_id.id,
            'sale_order_line_id': self.id
        })
        return res

    @api.multi
    def name_get(self):
        result = []
        for so_line in self.sudo():
            name = '%s - %s' % (
                so_line.order_id.name, so_line.name.split('\n')[0] if so_line.name else [] or so_line.product_id.name)
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
                to_location_id = self._transfer_district_to_location(line.to_location_id)
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
        location_obj = self.env['stock.location']
        filter_domain = []
        if partner_id.district_id if hasattr(partner_id, 'district_id') else False:
            filter_domain = [('name', '=', partner_id.district_id.name)]
        elif partner_id.city_id if hasattr(partner_id, 'city_id') else False:
            filter_domain = [('name', '=', partner_id.city_id.name)]

        if not filter_domain:
            filter_domain = [('name', '=', partner_id.name)]

        location_id = None
        if filter_domain:
            location_id = location_obj.search(filter_domain)

        if not location_id:
            # 保留取上级的默认客户位置
            location_id = partner_id.parent_id.property_stock_customer
        return location_id

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
    # TODO： fix me 需要加上时间的维度
    def _fetch_customer_contract(self, res):
        res = self.env['customer.aop.contract'].search([
            ('partner_id', '=', res.partner_id.id)
        ])
        return res[0] if res else False

    def _transfer_district_to_location(self, partner_id):
        location_obj = self.env['stock.location']
        filter_domain = []
        if partner_id.district_id:
            filter_domain = [('name', '=', partner_id.district_id.name)]
        elif partner_id.city_id:
            filter_domain = [('name', '=', partner_id.city_id.name)]

        if filter_domain:
            location_id = location_obj.search(filter_domain)
        else:
            # 保留取上级的默认客户位置
            location_id = partner_id.parent_id.property_stock_customer
        _logger.info({
            'location_id': location_id
        })
        return location_id

    # 查找 条款
    def _find_contract_line(self, contract_id, order_line):
        contract_line_ids = contract_id.mapped('delivery_carrier_ids')

        order_from_location_id = self._transfer_district_to_location(order_line.from_location_id)
        order_to_location_id = self._transfer_district_to_location(order_line.to_location_id)
        # 使用 product.template
        # product_template_id.product_variant_ids
        # TODO: 待定， 是否需要递归查询呢？
        # 暂定： 获取上级
        # delivery_ids = [line_id for line_id in contract_line_ids if
        #                 order_from_location_id.id == line_id.from_location_id.id and
        #                 order_to_location_id.id == line_id.to_location_id.id]

        delivery_ids = []

        for line_id in contract_line_ids:
            if order_from_location_id.id == line_id.from_location_id.id and    \
                    order_to_location_id.id == line_id.to_location_id.id:

                # 判断合同条款中是否存在"转到条款",如存在,获取"转到条款"
                line_id = line_id if not line_id.goto_delivery_carrier_id else line_id.goto_delivery_carrier_id
                delivery_ids.append(line_id)

        delivery_ids = list(set(delivery_ids))

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
        contract_id = self._fetch_customer_contract(res)
        if not contract_id:
            return res

        # 接车单创建
        # res.order_line.replenish_stock_picking_order()

        data = []
        for line_id in res.order_line:
            # 获取数据
            # 如果 delivery_carrier_id 存在多条条款，需要用户进行选择
            # 默认使用第一条
            delivery_carrier_id = self._find_contract_line(contract_id, line_id)
            service_product_id = self._find_service_product(delivery_carrier_id)
            service_product_ids = self._find_service_product_ids(delivery_carrier_id)
            route_id = self._find_contract_route_id(delivery_carrier_id)
            route_ids = self._find_contract_route_ids(delivery_carrier_id)

            allowed_carrier_ids = [x.id for x in delivery_carrier_id]
            # _logger.info({
            #     'route_ids': route_ids,
            #     'service_product_ids': service_product_ids
            # })
            tmp = {
                    'service_product_id': service_product_id.id if service_product_id else False,
                    'route_id': route_id.id if route_id else False,
                    'price_unit': delivery_carrier_id[0].fixed_price if delivery_carrier_id else 0,
                    'delivery_carrier_id': delivery_carrier_id[0].id if delivery_carrier_id else False,
                    'customer_contract_id': contract_id.id,
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

    @api.multi
    def action_confirm(self):

        # 判断。如果判断的结果是存在VIN不在路由上的。则先进行调度
        if self.dispatch_or_not():
            return self.change_vin_location_to_route()

        # # 先去填充一次VIN
        for order in self:
            order_line_ids = order.order_line
            for line_id in order_line_ids:
                if line_id.vin:
                    continue
                line_id._fill_order_line_vin_id()

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
        return res

    # # 取消的同时。删除
    # @api.multi
    # def action_cancel(self):
    #     res = super(SaleOrder, self).action_cancel()
    #
    #     self.mapped('picking_ids').unlink()
    #     return res

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
                if not stock_quant_ids.filtered(lambda x:
                                                x.location_id == from_location_id.id and x.lot_id.id == line.vin.id):
                    return True

        return False
