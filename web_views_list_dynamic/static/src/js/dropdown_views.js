/* /web_views_list_dynamic/static/src/js/dropdown_views.js defined in bundle 'web.assets_backend' */
odoo.define('web_views_list_dynamic.ViewsDropdown', function (require) {
    "use strict";
    var core = require('web.core');
    var config = require('web.config');
    var Widget = require('web.Widget');
    var _t = core._t;
    var QWeb = core.qweb;
    var ViewsDropdown = Widget.extend({
        template: 'web_views_list_dynamic.ViewsDropdown',
        init: function (parent, model) {
            this._super.apply(this, arguments);
            this.model = model;
        },
        willStart: function () {
            var def = this._rpc({
                kwargs: {model: this.model,},
                model: 'web_views_list_dynamic.view',
                method: 'get_views',
            }).then(function (result) {
                console.log(result);
            });
            return $.when(this._super.apply(this, arguments), def);
        },
    });
    return ViewsDropdown;
});
;
