odoo.define('aop_sale.purchase_order_invoice', function (require) {
    "use strict";
    let show_button_model = ['purchase.order'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {

            var self = this;

            let $buttons = self._super.apply(self, arguments);

            this.getSession().user_has_group('aop_sale.group_generate_purchase_order_invoice_button').then(function(has_group) {
                if(has_group) {
                    let tree_model = self.modelName;
                    let display_invoice = self.initialState.context['display_invoice'];

                    for (let i = 0; i < show_button_model.length; i++) {
                        if (tree_model == show_button_model[i] && display_invoice) {
                            let button2 = $("<button type='button' class='btn btn-primary btn-default'>生成结算清单</button>")
                                .click(self.proxy('generate_purchase_order_invoice'));
                            self.$buttons.append(button2);
                        }
                    }
                }
                return;
            })

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