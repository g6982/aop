# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AopContract(models.Model):
    _name = 'aop.contract'

    name = fields.Char('合同名称', required=True)

    partner_id = fields.Many2one('res.partner', 'Partner')

    serial_number = fields.Char(string='合同编号')

    version_id = fields.Many2one('contract.version', string="版本")

    serial_no = fields.Char(string='合同号')

    is_formal = fields.Boolean(string='正式合同', default=True)

    project_id = fields.Many2one('contract.project', string="项目")

    date_start = fields.Date('合同开始时间', required=True, default=fields.Date.today)

    date_end = fields.Date('合同结束时间')

    effective_date = fields.Date('合同生效日')

    expiry_date = fields.Date('合同失效日')

    source = fields.Char(string='合同来源')

    type = fields.Selection(
        [
            ('buyer', '需方合同'),
            ('supplier', '供方合同')
        ],
        string='合同类型',
        default='buyer')

    delivery_carrier_ids = fields.One2many('delivery.carrier', 'contract_id', string="合同条款")






class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    #partner_id = fields.Many2one('res.partner', 'Partner')

    product_id = fields.Many2one('product.product', string='货物', domain=[('type', '=', 'product')], required=False, ondelete='restrict')

    # aop_route_id = fields.Many2one('aop.route', 'Aop Route ID')
    aop_route_id = fields.One2many('aop.route', 'aop_id', 'Aop Route ID')

    aop_route_ids = fields.Many2many('aop.route', string='AOP route')

    contract_id = fields.Many2one('aop.contract', 'contract')

    route_id = fields.Many2one('stock.location.route', '路由')

    #service_product_id = fields.Many2one(string='服务产品', related='route_id.service_product_id')
    service_product_id = fields.Many2one('product.product', string='服务产品')










class ContractVersion(models.Model):
    _name = 'contract.version'

    name = fields.Char(string='版本')


class ContractProject(models.Model):
    _name = 'contract.project'

    name = fields.Char(string='项目')
