# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AopContract(models.Model):
    _name = 'aop.contract'
    _inherit = ['mail.thread']
    _description = 'AOP contract'
    _order = 'version_code desc, contract_version desc'

    name = fields.Char('name', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', index=True)
    serial_number = fields.Char(string='Contract number')

    version_id = fields.Many2one('contract.version', string="Version")

    # 小版本
    contract_version = fields.Float(string='Version', default=0.1)
    # 大版本号
    version_code = fields.Char('Version code')

    serial_no = fields.Char(string='Contract no')
    is_formal = fields.Boolean(string='Contract', default=True)
    project_id = fields.Many2one('contract.project', string="Project")
    date_start = fields.Date('Start date', required=True, default=fields.Date.today)
    date_end = fields.Date('End date')
    effective_date = fields.Date('Active date')
    expiry_date = fields.Date('Expire_date')
    source = fields.Char(string='Source')
    type = fields.Selection(
        [
            ('buyer', 'Buyer'),
            ('supplier', 'Supplier')
        ],
        string='Contract type',
        default='buyer')
    delivery_carrier_ids = fields.One2many('delivery.carrier', 'contract_id', copy=True,
                                           string="Contract terms")
    aging = fields.Float('Aging(day)', default=1)
    contract_rule_ids = fields.One2many('contract.stock.rule.line', 'rule_contract_id', 'Contract rule line')

    active = fields.Boolean(default=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft',
        string='State',
        track_visibility='always')

    period_month = fields.Integer('Period month', default=1)

    @api.onchange('delivery_carrier_ids')
    def onchange_rule_line(self):
        data = []
        for delivery_id in self.delivery_carrier_ids:
            # for route_id in delivery_id.route_ids:
            for rule_id in delivery_id.rule_service_product_ids:
                data.append((0, 0, {
                    'route_id': delivery_id.route_id.id,
                    'rule_id': rule_id.rule_id.id,
                    'service_product_id': rule_id.service_product_id.id
                }))
        self.contract_rule_ids = data

    def set_contract_state(self):
        self.write({
            'state': 'done',
            'active': True
        })

    @api.multi
    def toggle_active(self):
        res = super(AopContract, self).toggle_active()
        for line in self:
            line.state = 'done' if line.active else 'draft'
        return res

    def cancel_contract(self):
        if self.state == 'done' or self.active:
            self.write({
                'state': 'draft',
                'active': False
            })

    @api.model
    def create(self, vals):
        res = super(AopContract, self).create(vals)
        self.update_invoice_line_to_latest_contract_version(res)
        return res

    # 复制后，更改为正式合同
    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        data = self.copy_data()
        for line_data in data:
            # 精度问题
            contract_version = round(float(line_data.get('contract_version') + 0.1) * 1000, -1) / 1000
            line_data.update({
                'contract_version': contract_version if line_data.get('contract_version') else 0.1
            })
            # 条款行
            for line in line_data.get('delivery_carrier_ids'):
                line[2].update({
                    'name': str(line_data.get('contract_version')) + '/' + line[2].get('name') if line_data.get(
                        'contract_version') else str(0.1) + '/' + line[2].get('name')
                })
        res = super(AopContract, self).copy(default=data[0])
        return res

    # 当修改和新增时，更新最新版本
    @api.multi
    def write(self, vals):
        update_state = False
        if 'contract_version' in vals.keys():
            update_state = True
        res = super(AopContract, self).write(vals)
        if update_state:
            for line_id in self:
                self.update_invoice_line_to_latest_contract_version(line_id)
        return res

    # 定时更新结算清单行的最新合同版本号
    def update_invoice_line_to_latest_contract_version(self, records):
        for record_id in records:
            sql_update = '''
                        update account_invoice_line set 
                        latest_aop_contract_version = {latest_aop_contract_version} 
                        where partner_id = {partner_id} and 
                        (latest_aop_contract_version < {latest_aop_contract_version} or 
                        latest_aop_contract_version is null)
                    '''.format(
                latest_aop_contract_version=record_id.contract_version,
                partner_id=record_id.partner_id.id
            )
            self.env.cr.execute(sql_update)


class ContractVersion(models.Model):
    _name = 'contract.version'
    _sql_constraints = [('unique_version_name', 'unique(name)', 'The name must be unique!')]

    name = fields.Char(string='Version')


class ContractProject(models.Model):
    _name = 'contract.project'

    name = fields.Char(string='Project')


class ContractStockRule(models.Model):
    _name = 'contract.stock.rule.line'

    name = fields.Char('Name', readonly=True, related='rule_id.name')
    route_id = fields.Many2one('stock.location.route', 'Route')
    rule_id = fields.Many2one('stock.rule', 'Rule')
    service_product_id = fields.Many2one('product.product', string='Product', domain=[('type', '=', 'service')])
    rule_contract_id = fields.Many2one('aop.contract', 'Contract')
