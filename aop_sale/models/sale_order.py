# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError

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

    # 新增 服务产品
    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        res.update({
            'service_product_id': self.service_product_id.id,
            'vin_id': self.vin.id
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
            if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
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
                self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom,
                                                  line.to_location_id.parent_id.property_stock_customer,
                                                  line.name,
                                                  line.order_id.name, values)
            except UserError as error:
                raise UserError(error)
                return False
                errors.append(error.name)
        if errors:
            raise UserError('\n'.join(errors))
        return True


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection([('dispatch', 'Dispatch'), ('customer', 'Customer')], store=True,
                                  compute='_get_order_type')
    from_location_id = fields.Many2one('res.partner', 'From location')

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
        res = self.env['aop.contract'].search([
            ('partner_id', '=', res.partner_id.id)
        ])
        return res if res else False

    # 针对导入，根据货物，选择出对应的服务产品和路由，如果路由存在多个，默认选择第一条
    def _find_service_product(self, contract_id, order_line):
        contract_line_ids = contract_id.mapped('delivery_carrier_ids')

        # 使用 product.template
        # product_template_id.product_variant_ids
        # TODO: 待定， 是否需要递归查询呢？
        # 暂定： 获取上级
        delivery_id = [line_id for line_id in contract_line_ids if
                       order_line.product_id.id in line_id.product_template_id.product_variant_ids.ids and
                       order_line.from_location_id.parent_id == line_id.start_position and
                       order_line.to_location_id.parent_id == line_id.end_position]

        return delivery_id[0].service_product_id if delivery_id else False

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

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)

        # 获取合同
        contract_id = self._fetch_customer_contract(res)
        if not contract_id:
            return res

        data = []
        for line_id in res.order_line:
            # 获取数据
            service_product_id = self._find_service_product(contract_id, line_id)
            route_id = self._find_route_id(res, line_id)
            data.append(
                (1, line_id.id, {
                    'service_product_id': service_product_id.id if service_product_id else False,
                    'route_id': route_id.id if route_id else False
                })
            )

        if data:
            res.write({
                'order_line': data
            })
        return res

    @api.multi
    def action_confirm(self):
        for line in self.order_line:
            if not line.mapped('vin'):
                raise UserError(_('You can not make order until the product have vin or stock.'))
        return super(SaleOrder, self).action_confirm()
