/* /web_views_list_dynamic/static/src/js/list_controller.js defined in bundle 'web.assets_backend' */
odoo.define('web_views_list_dynamic.controller', function (require) {
    "use strict";
    var core = require('web.core');
    var session = require('web.session');
    var framework = require('web.framework');
    var crash_manager = require('web.crash_manager');
    var field_registry = require('web.field_registry');
    var ListController = require('web.ListController');
    var FieldDropdown = require('web_views_list_dynamic.FieldDropdown');
    var ViewsDropdown = require('web_views_list_dynamic.ViewsDropdown');
    var _t = core._t;
    var QWeb = core.qweb;
    ListController.include({
        custom_events: _.extend({}, ListController.prototype.custom_events, {update_fields: '_updateFields',}),
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$list_customize = this.$buttons.find('.mk_list_button_customize');
                this.fields_dropdown = this._createFieldsDropdown();
                this.fields_dropdown.appendTo(this.$list_customize);
            }
        },
        _createFieldsDropdown: function () {
            var state = this.model.get(this.handle);
            var fieldsInfo = state.fieldsInfo[this.viewType];
            var fieldsList = _.map(state.fields, function (value, key) {
                return {
                    id: key,
                    data: value,
                    description: value.string,
                    active: key in fieldsInfo && fieldsInfo[key].invisible == undefined,
                    invisible: key in fieldsInfo && fieldsInfo[key].invisible != undefined,
                };
            });
            return new FieldDropdown(this, fieldsList, fieldsInfo, this.renderer.arch.children);
        },
        _updateFields: function (event) {
            event.stopPropagation();
            var state = this.model.get(this.handle);
            state.fieldsInfo[this.viewType] = event.data.fields;
            this.renderer.arch.children = event.data.arch;
            this.update({fieldsInfo: state.fieldsInfo}, {reload: true});
        },
        _updateButtons: function (mode) {
            this._super.apply(this, arguments);
            this.$mode_switch.find('input[type="checkbox"]').prop('checked', !!this.editable);
        }
    });
});
;
