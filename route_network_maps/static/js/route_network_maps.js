odoo.define('route_network_maps.show_maps', function (require) {
    "use strict";

    let FormView = require('web.FormView');
    let FormController = require('web.FormController');
    let FormRenderer = require('web.FormRenderer');

    FormView.extend({
        events: {
            'click #map_id': function (env) {
                 console.log('hello world');
            }
        }
    });

});