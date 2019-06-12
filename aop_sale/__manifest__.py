# -*- coding: utf-8 -*-
{
    'name': "aop_sale",

    'summary': "中集AOP",
    'description': """
        中集AOP
    """,
    'author': "1di0t",
    'depends': ['account', 'sale', 'fleet', 'stock', 'sale_management', 'purchase', 'delivery', 'stock_picking_batch'],
    'data': [
        'security/ir.model.access.csv',
        'views/insurance_management.xml',
        'views/service_product.xml',
        'views/aop_contract.xml',
        'views/delivery_carrier.xml',
        'views/sale_order_view.xml',
        'views/stock_move.xml',
        'views/menu.xml',
    ],
}
