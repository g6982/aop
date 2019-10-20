odoo.define('aop_sale.write_off_batch', function (require) {
    "use strict";
    let show_button_model = ['handover.vin'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            var self = this;

            let $buttons = this._super.apply(this, arguments);

            this.getSession().user_has_group('aop_sale.group_create_write_off_batch_button').then(function(has_group) {

                if(has_group) {
                    let tree_model = self.modelName;
                    let display_invoice = self.initialState.context['type'];

                    for (let i = 0; i < show_button_model.length; i++) {
                        if (tree_model == show_button_model[i]) {
                            let button2 = $("<button type='button' class='btn btn-primary btn-default'>生成核销批次</button>")
                                .click(self.proxy('create_write_off_batch'));
                            self.$buttons.append(button2);
                        }
                    }
                }
                return;
            })
            return $buttons;
        },
        create_write_off_batch: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'write.off.line.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids, 'current_model_name': 'handover.vin'},
                view_id: 'view_write_off_order_line_wizard_form',
                target: 'new',
            });
        },
    });

});