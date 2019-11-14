# -*- coding: utf-8 -*-
{
    "name": "AOP interface",
    "version": "1.0.0",
    "category": "API",
    "author": "1di0t",
    "summary": "AOP interface",
    "support": "dgqcjx@gmail.com",
    "description": """ AOP-WMS """,
    "depends": ["web", 'stock', 'base'],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_param.xml",
        "views/ir_model.xml",
        "views/res_users.xml",
        "views/menu.xml",
        "views/done_picking_view.xml",
        "views/interface_config_setting.xml",
    ],
    "installable": True,
    "auto_install": False,
}
