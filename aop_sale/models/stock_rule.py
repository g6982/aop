# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    service_product_id = fields.Many2one('product.product', string='Service product',
                                         related='picking_type_id.service_product_id')
    action = fields.Selection(
        selection=[
            ('pull', 'Pull From'),
            ('push', 'Push To'),
            ('pull_push', 'Pull & Push'),
            ('buy', 'Buy')],
        string='Action',
        required=True, default='pull')

    procure_method = fields.Selection([
        ('make_to_stock', 'Take From Stock'),
        ('make_to_order', 'Trigger Another Rule')], string='Move Supply Method',
        default='make_to_order', required=True,
        help="""Create Procurement: A procurement will be created in the source location and the system will try to find a rule to resolve it. The available stock will be ignored.
                 Take from Stock: The products will be taken from the available stock.""")

    is_station_line = fields.Boolean('Is station', default=False)

    # 添加服务产品到stock.picking
    def _get_custom_move_fields(self):
        res = super(StockRule, self)._get_custom_move_fields()
        res += ['service_product_id', 'vin_id', 'delivery_carrier_id', 'delivery_to_partner_id', 'sale_order_line_id']
        return res

    # 获取库存产品的位置
    def _get_product_stock_location(self, product_id, vin_id):
        stock_quant_id = self.env['stock.quant'].search([
            ('product_id', '=', product_id.id),
            ('lot_id', '=', vin_id),
            ('quantity', '>', 0),
            ('reserved_quantity', '=', 0),
            ('location_id.usage', '=', 'internal')
        ]) if vin_id else False
        # _logger.info({
        #     'stock_quant_id': stock_quant_id
        # })
        return stock_quant_id.location_id.id if stock_quant_id else False

    def _run_pull(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        product_stock_id = self._get_product_stock_location(product_id, values.get('vin_id', False))
        if location_id.id == product_stock_id if product_stock_id else False:
            _logger.info({
                'date_plannedvalues': values.get('date_planned')
            })
            return True

        res = super(StockRule, self)._run_pull(product_id, product_qty, product_uom, location_id, name, origin, values)
        return res

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        res = super(StockRule, self)._get_stock_move_values(
            product_id,
            product_qty,
            product_uom,
            location_id,
            name,
            origin,
            values,
            group_id
        )

        date_expected = self._get_date_expected_rule(self.route_id, values)

        res.update({
            'date': date_expected,
            'date_expected': date_expected
        })
        return res

    # date_planned = 订单的确认日期 + 订单行的交货提前时间 + 路由标准实效 + 公司的security_lead - 规则的 delay
    def _get_date_expected_rule(self, route_id, values):
        all_rule_ids = route_id.rule_ids.sorted(lambda x: x.id)
        # 如果是第一条，则不做处理？
        # 第二条，减去第一条的delay, 依次
        if all_rule_ids.ids[-1] == self.id:
            date_expected = values['date_planned']
        else:
            current_record_index = all_rule_ids.ids.index(self.id)
            previous_record_id = all_rule_ids[current_record_index + 1]
            date_expected = fields.Datetime.to_string(
                fields.Datetime.from_string(values['date_planned']) - relativedelta(days=previous_record_id.delay or 0)
            )
        return date_expected
