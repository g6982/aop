/* /muk_web_views_list_dynamic/static/src/js/dropdown_fields.js defined in bundle 'web.assets_backend' */
odoo.define('muk_web_views_list_dynamic.FieldDropdown', function (require) {
    "use strict";
    var core = require('web.core');
    var config = require('web.config');
    var field_registry = require('web.field_registry');
    var Widget = require('web.Widget');
    var QWeb = core.qweb;
    var _t = core._t;
    var FieldDropdown = Widget.extend({
        template: 'muk_web_views_list_dynamic.FieldsDropdown',
        fieldTemplate: 'muk_web_views_list_dynamic.FieldsDropdownItems',
        events: {
            'click .o_menu_item': '_onFieldClick',
            'click .mk_list_customize_fields_reset': '_onResetClick',
            'input .mk_list_customize_fields_search input': '_onSearch',
        },
        init: function (parent, fields, info, arch) {
            this._super.apply(this, arguments);
            this.info = $.extend(true, {}, info);
            var active_fields = _.object(_.map($.extend(true, {}, arch), function (value, sequence) {
                return [value.attrs.name, sequence]
            }));
            var fields = _.map(fields, function (field, sequence) {
                if (field.id in active_fields) {
                    field.sequence = parseInt(active_fields[field.id]);
                } else {
                    field.sequence = sequence + 1000;
                }
                return field;
            });
            this.fields = _.sortBy(fields, function (field) {
                return field.sequence;
            });
            this.arch = _.object(_.map($.extend(true, {}, arch), function (value) {
                return [value.attrs.name, value]
            }));
        },
        start: function () {
            this.$menu = this.$('.o_dropdown_menu');
            this.$search = this.$('.mk_list_customize_fields_search');
            this.$menu.sortable({
                axis: "y",
                items: "> .o_menu_item",
                containment: "parent",
                update: this._onFieldMove.bind(this),
            });
        },
        updateFieldActiveStatus: function (ids) {
            _.each(this.fields, function (field) {
                field.active = _.contains(ids, field.id);
            });
            this._updateDropdownFields();
        },
        _updateDropdownFields: function () {
            this.$menu.find('.o_menu_item').remove();
            this.$search.after($(QWeb.render(this.fieldTemplate, {widget: this})));
        },
        _onFieldMove: function (event) {
            var keys = {};
            _.each(event.target.children, function (element, sequence) {
                var $element = $(element);
                if ($element.hasClass("o_menu_item")) {
                    keys[$element.data('id')] = sequence;
                }
            });
            this.fields = _.sortBy(this.fields, function (field) {
                return keys[field.id];
            });
            this._notifyFieldsUpdate();
        },
        _onFieldClick: function (event) {
            event.preventDefault();
            event.stopPropagation();
            var field = _.findWhere(this.fields, {id: $(event.currentTarget).data('id')});
            field.active = !field.active;
            this._updateDropdownFields();
            this._notifyFieldsUpdate();
        },
        _onResetClick: function (event) {
            this.fields = _.sortBy(this.fields, function (field) {
                return field.sequence;
            });
            this.updateFieldActiveStatus(_.keys(this.info));
            this.trigger_up('update_fields', {arch: _.values(this.arch), fields: this.info,});
        },
        _onSearch: _.debounce(function (event) {
            var search = $(event.currentTarget).val().toLowerCase();
            _.each(this.fields, function (field) {
                field.invisible = search ? field.description.toLowerCase().indexOf(search) < 0 : false;
            });
            this._updateDropdownFields();
        }, 250),
        _notifyFieldsUpdate: function (event) {
            this.trigger_up('update_fields', {arch: this._getArch(), fields: this._getFieldInfo(),});
        },
        _getArch: function () {
            var arch = [];
            _.each(this.fields, function (field) {
                if (field.active && field.id in this.arch) {
                    arch.push(this.arch[field.id]);
                } else if (field.active && !(field.id in this.arch)) {
                    arch.push({
                        attrs: {
                            modifiers: {readonly: field.data.readonly, required: field.data.required,},
                            name: field.id,
                        }, children: [], tag: "field",
                    });
                }
            }, this);
            return arch;
        },
        _getFieldInfo: function () {
            var info = {};
            _.each(this.fields, function (field) {
                if (field.id in this.info) {
                    info[field.id] = $.extend(true, {}, this.info[field.id]);
                    info[field.id].modifiers = _.extend({}, info[field.id].modifiers, {column_invisible: !field.active,});
                    info[field.id].invisible = !field.active;
                } else if (field.active && !(field.id in this.info)) {
                    var type = field.data.type;
                    var attrs = {
                        Widget: field_registry.getAny(["list." + type, type, "abstract"]),
                        modifiers: {readonly: field.data.readonly, required: field.data.required,}
                    };
                    if (type === 'one2many' || type === 'many2many') {
                        if (attrs.Widget.prototype.useSubview) {
                            attrs.views = {};
                        }
                        if (attrs.Widget.prototype.fieldsToFetch) {
                            attrs.viewType = 'default';
                            attrs.relatedFields = _.extend({}, attrs.Widget.prototype.fieldsToFetch);
                            attrs.fieldsInfo = {
                                'default': _.mapObject(attrs.Widget.prototype.fieldsToFetch, function () {
                                    return {};
                                }),
                            };
                        }
                        if (attrs.Widget.prototype.fieldDependencies) {
                            attrs.fieldDependencies = attrs.Widget.prototype.fieldDependencies;
                        }
                    }
                    info[field.id] = attrs;
                }
            }, this);
            return info;
        },
    });
    return FieldDropdown;
});
;
