odoo.define('aop_sale.verify_batch', function (require) {
    "use strict";
    let show_button_model = ['batch.reconciliation.number'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            var self = this;

            let $buttons = this._super.apply(this, arguments);

            this.getSession().user_has_group('aop_sale.group_verify_reconciliation_file_button').then(function(has_group) {

                if(has_group) {
                    let tree_model = self.modelName;
                    let display_invoice = self.initialState.context['type'];

                    for (let i = 0; i < show_button_model.length; i++) {
                        if (tree_model == show_button_model[i]) {
                            let button2 = $("<button type='button' class='btn btn-primary btn-default'>生成审核批次</button>")
                                .click(self.proxy('verify_reconciliation_file'));
                            self.$buttons.append(button2);
                        }
                    }
                }
                return;
            })
            return $buttons;
        },
        verify_reconciliation_file: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'package.reconciliation.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids, 'current_model_name': 'batch.reconciliation.number'},
                view_id: 'view_package_reconciliation_list_wizard',
                target: 'new',
            });
        },
    });

});