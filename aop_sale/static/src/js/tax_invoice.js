odoo.define('aop_sale.tax_invoice', function (require) {
    "use strict";
    let show_button_model = ['account.invoice'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            let $buttons = this._super.apply(this, arguments);
            let tree_model = this.modelName;
            for (let i = 0; i < show_button_model.length; i++) {
                if (tree_model == show_button_model[i]) {
                    let button2 = $("<button type='button' class='btn btn-sm btn-primary btn-default'>创建税务发票</button>")
                        .click(this.proxy('generate_tax_invoice'));
                    this.$buttons.append(button2);
                }
            }
            return $buttons;
        },
        generate_tax_invoice: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'account.tax.invoice.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids},
                view_id: 'view_account_tax_invoice_wizard',
                target: 'new',
            });
        },
    });

});