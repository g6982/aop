# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError
from odoo.addons.sale_stock.models.sale_order import SaleOrder as InheritSaleOrder
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    vin = fields.Many2one('stock.production.lot', 'VIN', domain="[('product_id','=', product_id)]")

    service_product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)],
                                         ondelete='restrict')
    from_location_id = fields.Many2one('res.partner', 'From location')
    to_location_id = fields.Many2one('res.partner', 'To location')
    delivery_count = fields.Integer('Count', related='order_id.delivery_count')

    handover_number = fields.Char('Handover number')

    contract_id = fields.Many2one('aop.contract', 'Contract')
    customer_contract_id = fields.Many2one('customer.aop.contract', 'Contract')

    delivery_carrier_id = fields.Many2one('delivery.carrier', 'Delivery carrier',
                                          compute='_get_delivery_carrier_id', store=True)

    vin_code = fields.Char('VIN Code')

    # 部分完成的情况
    state = fields.Selection(selection_add=[('part_done', 'Part done')])

    # 针对单条订单行，也能创建stock,picking，而不影响整个的状态
    stock_picking_state = fields.Boolean('Picking state', compute='_compute_stock_picking_state', copy=False)
    stock_picking_ids = fields.Many2many('stock.picking', string='Pickings', copy=False)

    allowed_route_ids = fields.Many2many('stock.location.route', copy=False)
    allowed_service_product_ids = fields.Many2many('product.product', domain=[('sale_ok', '=', True)], copy=False)

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

    @api.depends('route_id', 'from_location_id', 'to_location_id')
    def _get_delivery_carrier_id(self):
        for order_line in self:
            if order_line.route_id and order_line.from_location_id and order_line.to_location_id:
                from_location_id = self._transfer_district_to_location(order_line.from_location_id)
                to_location_id = self._transfer_district_to_location(order_line.to_location_id)
                search_domain = [
                    ('customer_contract_id', '=', order_line.customer_contract_id.id),
                    ('route_id', '=', order_line.route_id.id),
                    ('from_location_id', '=', from_location_id.id),
                    ('to_location_id', '=', to_location_id.id)
                ]
                delivery_id = self.env['delivery.carrier'].search(search_domain)

                # 多条条款，对应相同的路由，不同的服务产品
                if delivery_id:
                    route_ids = delivery_id.mapped('route_id')
                    service_product_ids = delivery_id.mapped('service_product_id')
                    # 设置过滤规则
                    order_line.allowed_route_ids = [(6, 0, route_ids.ids)]
                    order_line.allowed_service_product_ids = [(6, 0, service_product_ids.ids)]

                    delivery_id = delivery_id[0]
                    order_line.delivery_carrier_id = delivery_id.id
                    order_line.service_product_id = delivery_id.service_product_id.id
                    order_line.price_unit = delivery_id.service_product_id.list_price
            else:
                if order_line.from_location_id and order_line.to_location_id:
                    from_location_id = self._transfer_district_to_location(order_line.from_location_id)
                    to_location_id = self._transfer_district_to_location(order_line.to_location_id)
                    search_domain = [
                        ('customer_contract_id', '=', order_line.customer_contract_id.id),
                        ('from_location_id', '=', from_location_id.id),
                        ('to_location_id', '=', to_location_id.id)
                    ]
                    delivery_id = self.env['delivery.carrier'].search(search_domain)
                    route_ids = delivery_id.mapped('route_id')
                    service_product_ids = delivery_id.mapped('service_product_id')

                    order_line.allowed_route_ids = [(6, 0, route_ids.ids)]
                    order_line.allowed_service_product_ids = [(6, 0, service_product_ids.ids)]

                order_line.delivery_carrier_id = False
                order_line.service_product_id = False

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
            _logger.info({
                'line.stock_picking_state': line.stock_picking_state
            })
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

        if filter_domain:
            location_id = location_obj.search(filter_domain)
        else:
            # 保留取上级的默认客户位置
            location_id = partner_id.parent_id.property_stock_customer
        # _logger.info({
        #     'location_id': location_id
        # })
        return location_id


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection([('dispatch', 'Dispatch'), ('customer', 'Customer')], store=True,
                                  compute='_get_order_type')
    from_location_id = fields.Many2one('res.partner', 'From location')

    # 部分完成的情况
    state = fields.Selection(selection_add=[('part_done', 'Part done')])

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
        delivery_ids = [line_id for line_id in contract_line_ids if
                        order_from_location_id.id == line_id.from_location_id.id and
                        order_to_location_id.id == line_id.to_location_id.id]

        _logger.info({
            'delivery_ids': delivery_ids
        })
        return delivery_ids

    # 针对导入，根据货物，选择出对应的服务产品和路由，如果路由存在多个，默认选择第一条
    def _find_service_product(self, contract_line):
        return contract_line[0].service_product_id if contract_line else False

    # 过滤
    def _find_service_product_ids(self, contract_line):
        return [line.mapped('service_product_id').id for line in contract_line if line.mapped('service_product_id')] if contract_line else False

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
        return [line.mapped('route_id').id for line in contract_line if line.mapped('route_id')] if contract_line else False

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)

        # 获取合同
        contract_id = self._fetch_customer_contract(res)
        if not contract_id:
            return res
        # _logger.info({
        #     'contract_id': contract_id
        # })
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

            _logger.info({
                'route_ids': route_ids,
                'service_product_ids': service_product_ids
            })
            data.append(
                (1, line_id.id, {
                    'service_product_id': service_product_id.id if service_product_id else False,
                    'route_id': route_id.id if route_id else False,
                    # 'price_unit': service_product_id.list_price if service_product_id else 1,
                    'price_unit': service_product_id.standard_price if service_product_id else 1,
                    'delivery_carrier_id': delivery_carrier_id[0].id if delivery_carrier_id else False,
                    'customer_contract_id': contract_id.id,
                    'allowed_service_product_ids': [(6, 0, service_product_ids)] if service_product_ids else False,
                    'allowed_route_ids': [(6, 0, route_ids)] if route_ids else False
                })
            )

        if data:
            res.write({
                'order_line': data
            })
        return res

    @api.multi
    def action_confirm(self):
        if not any([True if line.mapped('vin') else False for line in self.order_line]):
            raise UserError(_('You can not make order until the product have vin or stock.'))
        res = super(SaleOrder, self).action_confirm()

        # FIXME: 补丁
        self.picking_ids.filtered(
            lambda picking: picking.state == 'confirmed').action_assign() if self.picking_ids.filtered(
            lambda picking: picking.state == 'confirmed') and not self.picking_ids.filtered(
            lambda picking: picking.state == 'assigned') else False

        for order in self:
            order.mapped('order_line')._compute_stock_picking_state()
            if not all(order.mapped('order_line').mapped('stock_picking_state')):
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
            order_line_ids = order.order_line.filtered(lambda x: x.stock_picking_state is False)
            if order_line_ids:
                order_line_ids._action_launch_stock_rule()

            order_line_ids._compute_stock_picking_state()
            if all(order.order_line.mapped('stock_picking_state')):
                order.write({
                    'state': 'sale'
                })
