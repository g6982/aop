odoo.define('aop_sale.verify_tax_invoice', function (require) {
    "use strict";
    let show_button_model = ['verify.batch.reconciliation'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            var self = this;

            let $buttons = this._super.apply(this, arguments);

            this.getSession().user_has_group('aop_sale.group_generate_tax_invoice_button').then(function(has_group) {

                if(has_group) {
                    let tree_model = self.modelName;
                    let display_invoice = self.initialState.context['type'];

                    for (let i = 0; i < show_button_model.length; i++) {
                        if (tree_model == show_button_model[i]) {
                            let button2 = $("<button type='button' class='btn btn-primary btn-default'>创建税务发票</button>")
                                .click(self.proxy('verify_generate_tax_invoice'));
                            self.$buttons.append(button2);
                        }
                    }
                }
                return;
            })
            return $buttons;
        },
        verify_generate_tax_invoice: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'account.tax.invoice.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids, 'current_model_name': 'verify.batch.reconciliation'},
                view_id: 'view_account_tax_invoice_wizard',
                target: 'new',
            });
        },
    });

});