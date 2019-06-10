# -*- coding: utf-8 -*-
{
    'name': "aop_sale",

    'summary': "中集AOP",
    'description': """
        中集AOP
    """,
    'author': "1di0t",
    'depends': ['account', 'sale', 'fleet', 'stock', 'sale_management', 'purchase'],
    'data': [
        'views/sale_order_view.xml',
        'views/stock_move.xml',
    ],
}
