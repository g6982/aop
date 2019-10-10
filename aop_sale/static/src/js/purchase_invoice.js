odoo.define('aop_sale.purchase_order_invoice', function (require) {
    "use strict";
    let show_button_model = ['purchase.order'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            let $buttons = this._super.apply(this, arguments);
            let tree_model = this.modelName;
            let display_invoice = this.initialState.context['display_invoice'];

            for (let i = 0; i < show_button_model.length; i++) {
                if (tree_model == show_button_model[i] && display_invoice) {
                    let button2 = $("<button type='button' class='btn btn-sm btn-primary btn-default'>生成结算清单</button>")
                        .click(this.proxy('generate_purchase_order_invoice'));
                    this.$buttons.append(button2);
                }
            }
            return $buttons;
        },
        generate_purchase_order_invoice: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'purchase.order.invoice.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids},
                view_id: 'view_purchase_invoice_wizard_form',
                target: 'new',
            });
        },
    });

});