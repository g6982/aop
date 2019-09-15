# -*- coding: utf-8 -*-
{
    'name': "aop_sale",

    'summary': "中集AOP",
    'description': """
        中集AOP
    """,
    'author': "1di0t",
    'depends': ['account', 'sale', 'fleet', 'stock', 'sale_management',
                'purchase', 'delivery', 'stock_picking_batch',
                'barcodes', 'delivery_hs_code', 'account_period', 'mail'],
    'data': [
        'security/aop_contract_group.xml',
        'security/access_group.xml',
        'security/ir.model.access.csv',
        'data/stock_data.xml',
        'views/insurance_management.xml',
        'views/service_product.xml',
        'views/mass_loss.xml',
        'views/customer_aop_contract.xml',
        'views/supplier_aop_contract.xml',
        'views/contract_version.xml',
        'views/delivery_carrier.xml',
        'views/sale_order_view.xml',
        'views/stock_move.xml',
        'views/account_invoice.xml',
        'views/account_tax_invoice.xml',
        'views/stock_warehouse.xml',
        'views/stock_rule_view.xml',
        'views/stock_picking.xml',
        'views/stock_picking_type.xml',
        'views/stock_picking_batch.xml',
        'views/stock_location_views.xml',
        'views/purchase_order.xml',
        'views/product_template.xml',
        'views/product_product.xml',
        'views/base_warehouse.xml',
        'views/account_account_view.xml',
        'views/stock_location_route.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/menu.xml',
        'views/restricted_menu.xml',
        'views/base.xml',
        'views/dispatch_order.xml',
        'wizard/account_tax_invoice_wizard.xml',
        'wizard/change_stock_picking.xml',
        'wizard/import_sale_order.xml',
        'wizard/import_dispatch_order.xml',
        'wizard/sale_make_invoice_advance_view.xml',
        'wizard/fill_service_product_wizard.xml',
        'wizard/statement_report.xml',
        'wizard/write_off_order_line.xml',
        'wizard/month_close.xml',
        'report/report_statement.xml',
    ],
}
