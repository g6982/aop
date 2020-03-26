#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import werkzeug
import odoo
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class LogisticsManageWarehouse(http.Controller):
    @http.route('/logistics_warehouse_manage', auth="public", website=True, csrf=False)
    def show_logistics_warehouse_manage(self, *args, **kw):
        qcontext = self.get_qcontext()
        _logger.info({
            'qcontext': qcontext
        })
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            warehouse_name = qcontext.get('warehouse_name')
            warehouse_code = qcontext.get('warehouse_code')
            warehouse_location_name = qcontext.get('warehouse_location_name')
            warehouse_service_area = qcontext.get('warehouse_service_area')

            current_partner_id = request.env.user.partner_id.id

            warehouse_obj = request.env['stock.warehouse'].sudo()
            warehouse_id = warehouse_obj.search([
                ('belong_partner_id', '=', current_partner_id),
                ('code', '=', warehouse_code)
            ])

            tmp_delivery_data = {
                'belong_partner_id': current_partner_id,
                'name': warehouse_name,
                'code': warehouse_code,
                'location_name': warehouse_location_name,
                'service_area': warehouse_service_area,
            }

            if not warehouse_id:
                warehouse_id.create(tmp_delivery_data)
            else:
                warehouse_id.write(tmp_delivery_data)

            return request.render('website.logistics_warehouse_manage_success')

        return request.render('website.logistics_warehouse_manage')

    def get_qcontext(self):
        qcontext = request.params.copy()

        # Check
        values = {key: qcontext.get(key) for key in (
            'warehouse_name', 'warehouse_code', 'warehouse_location_name', 'warehouse_service_area')}
        if not values:
            raise UserError(_("The form was not properly filled in."))

        return qcontext

    @http.route('/logistics_warehouse_manage_success', auth="public", website=True, csrf=False)
    def logistics_supplier_manage_success(self, *args, **kw):
        return request.render('website.logistics_warehouse_manage_success')

    @http.route(['/manage/warehouse/edit'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })

        if post:
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in self.MANDATORY_BILLING_FIELDS}
                values.update({key: post[key] for key in self.OPTIONAL_BILLING_FIELDS if key in post})
                values.update({'zip': values.pop('zipcode', '')})
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({
            'partner': partner,
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'redirect': redirect,
            'page_name': 'my_details',
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response