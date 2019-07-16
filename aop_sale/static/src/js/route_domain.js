odoo.define('aop_sale.route_domain', function (require) {
    "use strict";

    var core = require('web.core');
    let Widget = require('web.Widget');
    var section_and_note_one2many = core.form_widget_registry.get('section_and_note_one2many');

    console.log(section_and_note_one2many);
    let route_domain = Widget.extend({
        events: {
            "click .order_line_route_id div input": "get_route_domain",
        },

        get_route_domain: function () {
            console.log('hello world!!!');
        },

    });
    return route_domain;
});
