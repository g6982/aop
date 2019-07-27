# -*_ coding :utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class StockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    service_product_id = fields.Many2one('product.product', string='Service product')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        partner_id = self._context.get('sale_filter_route_id_by_partner')
        if partner_id:
            contract = self.env['customer.aop.contract'].search([
                ('partner_id', '=', partner_id)
            ])
            _route_ids = []

            for line in contract.delivery_carrier_ids:
                _route_id = self.env['stock.location.route'].search([
                    ('service_product_id', '=', line.service_product_id.id),
                    ('sale_selectable', '=', True)
                ])
                for route_line in _route_id:
                    _route_ids.append(route_line.id)
            domain = expression.AND([
                args or [],
                [('id', 'in', _route_ids)]
            ])
            route_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
            return self.browse(route_ids).name_get()

        return super(StockLocationRoute, self)._name_search(name, args=args, operator=operator, limit=limit,
                                                            name_get_uid=name_get_uid)
