# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'

    parent_id = fields.Many2one(
        'account.account', 'Parent Account', index=True, ondelete='cascade')
    child_ids = fields.One2many('account.account', 'parent_id', 'Contains')
    parent_path = fields.Char(index=True)

    @api.multi
    @api.constrains('parent_id')
    def check_recursion(self):
        for account in self:
            if not super(AccountAccount, account)._check_recursion():
                raise UserError(
                    _('You can not create recursive analytic accounts.'),
                )
