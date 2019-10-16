/* /muk_web_views_list_dynamic/static/src/js/list_controller.js defined in bundle 'web.assets_backend' */
odoo.define('muk_web_views_list_dynamic.controller', function (require) {
    "use strict";
    var core = require('web.core');
    var session = require('web.session');
    var framework = require('web.framework');
    var crash_manager = require('web.crash_manager');
    var field_registry = require('web.field_registry');
    var ListController = require('web.ListController');
    var FieldDropdown = require('muk_web_views_list_dynamic.FieldDropdown');
    var _t = core._t;
    var QWeb = core.qweb;
    ListController.include({
        custom_events: _.extend({}, ListController.prototype.custom_events, {update_fields: '_updateFields',}),
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$mode_switch = $(QWeb.render('muk_web_utils.switch', {
                    id: 'mk-list-switch-' + this.controllerID,
                    label: _t("Editable"),
                }));
                this.$buttons.find('.mk_list_button_switch').html(this.$mode_switch);
                this.$buttons.on('click', '.mk_list_button_export', this._onExportView.bind(this));
                this.$mode_switch.on('change', 'input[type="checkbox"]', this._onSwitchMode.bind(this));
                this.$mode_switch.find('input[type="checkbox"]').prop('checked', !!this.editable);
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
        },
        _onExportView: function () {
            var renderer = this.renderer;
            var record = this.model.get(this.handle);
            console.log(renderer.columns);
            var fields = _.map(renderer.columns.filter(c => c.tag == "field"), function (field) {
                var name = field.attrs.name;
                var description = field.attrs.widget ? renderer.state.fieldsInfo.list[name].Widget.prototype.description : field.attrs.string || renderer.state.fields[name].string;
                return {name: name, label: description || name}
            });
            var data = {
                import_compat: false,
                model: record.model,
                fields: fields,
                ids: record.res_ids || [],
                domain: record.getDomain(),
                context: record.getContext(),
            }
            framework.blockUI();
            session.get_file({
                url: '/web/export/xls',
                data: {data: JSON.stringify(data)},
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager)
            });
        },
        _onSwitchMode: function (event) {
            var editable = $(event.currentTarget).is(':checked');
            if (editable) {
                this.editable = 'top';
                this.renderer.editable = this.editable;
            } else {
                this.editable = false;
                this.renderer.editable = false;
            }
            this.update({}, {reload: true}).then(this._updateButtons.bind(this, 'readonly'));
        }
    });
});
;