odoo.define('aop_sale.change_stock_picking', function (require) {
    "use strict";
    let show_button_model = ['stock.picking'];
    let ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {

            var self = this;

            let $buttons = this._super.apply(this, arguments);
            this.getSession().user_has_group('aop_sale.group_change_stock_picking_wizard_button').then(function(has_group) {
                if(has_group) {
                    let tree_model = self.modelName;
                    for (let i = 0; i < show_button_model.length; i++) {
                        if (tree_model == show_button_model[i]) {
                            let button2 = $("<button type='button' class='btn btn-primary btn-default'>更改任务</button>")
                                .click(self.proxy('change_stock_picking_wizard'));
                            self.$buttons.append(button2);
                        }
                    }
                }
                return;
            })
            return $buttons;
        },
        change_stock_picking_wizard: function () {
            let selected_ids = this.getSelectedIds();
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'change.stock.picking.wizard',
                views: [[false, 'form']],
                view_mode: "form",
                view_type: 'form',
                context: {'active_ids': selected_ids},
                view_id: 'view_change_stock_picking_form',
                target: 'new',
            });
        },
    });

});