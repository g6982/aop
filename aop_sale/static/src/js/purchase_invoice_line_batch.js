odoo.define('aop_sale.purchase_invoice_line', function (require) {
    "use strict";
    let show_button_model = ['account.invoice.line'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {

            var self = this;

            let $buttons = self._super.apply(self, arguments);

            let tree_model = self.modelName;

            for (let i = 0; i < show_button_model.length; i++) {
                if (tree_model == show_button_model[i]) {
                    let button2 = $("<button type='button' class='btn btn-primary btn-default'>打包付款结算清单行</button>")
                        .click(self.proxy('batch_purchase_invoice_line'));
                    self.$buttons.append(button2);
                }
            }

            return $buttons;
        },
        batch_purchase_invoice_line: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'batch.purchase.invoice.line.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids},
                view_id: 'view_batch_purchase_invoice_line_wizard_form',
                target: 'new',
            });
        },
    });

});