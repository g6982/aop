# -*- coding: utf-8 -*-
{
    'name': "aop_sale",

    'summary': "中集AOP",
    'description': """
        中集AOP
    """,
    'author': "1di0t",
    'depends': ['account', 'sale', 'fleet', 'stock', 'sale_management', 'purchase', 'delivery', 'stock_picking_batch',
                'barcodes', 'delivery_hs_code', 'account_period'],
    'data': [
        'security/access_group.xml',
        'security/ir.model.access.csv',
        'views/insurance_management.xml',
        'views/service_product.xml',
        'views/mass_loss.xml',
        'views/aop_contract.xml',
        'views/delivery_carrier.xml',
        'views/sale_order_view.xml',
        'views/stock_move.xml',
        'views/account_invoice.xml',
        'views/account_tax_invoice.xml',
        'views/stock_warehouse.xml',
        'views/stock_rule_view.xml',
        'views/stock_picking.xml',
        'views/base_warehouse.xml',
        'views/stock_location_route.xml',
        'views/menu.xml',
        'views/base.xml',
        'views/dispatch_order.xml',
        'wizard/account_tax_invoice_wizard.xml',
        'wizard/change_stock_picking.xml',
        'wizard/import_sale_order.xml',
    ],
}
