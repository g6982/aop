# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Pack/Bundle on Sales and Delivery',
    'version': '1.0',
    'category' : 'Sales',
    'license': 'Other proprietary',
    'price': 15.0,
    'currency': 'EUR',
    'summary': """This module allow you to Create Pack / Bundle products and add it to Sales order and Delivery Orders.""",
    'description': """
Allow Sales users to create Pack / Bundle Products.
Allow add products into the Pack / Bundle.
It will allowed to add Bundle Products into the Sale order.
It will add all the Products into the Sale order which bundle was add.
It will allowed to add Pack / Bundle in to the stock picking also.
It will add all the products on the movelines.
For more details please see Video in Live Preview.
Is Bundled Product
Add Products as the bundle product
Create Sale order
Add Pack / Bundle
Add Pack / Bundle Products
Create Stock Pickcing
Add Pack / Bundle
Add Pack / Bundle Products
Add all kind of the products as the Pack / Bundle Products
wk_product_pack
PRODUCT PACK
website bundle pack
product_bundle_pack
Product Bundle Pack
Combo packs
Created Product Packs
Sales
Odoo Product Pack
Sales/Sales
Sales/Sales/Bundle Products
Pack and its products in Picking
Odoo Pack
Odoo Pack / Bundle Product
Bundle Products
bundle product
product pack
pack product
product bundle

    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    'live_test_url': 'https://youtu.be/gkU-pnHNUGc',
    'depends': [
            'sale',
            'stock',
    ],
    'data':[
        'security/ir.model.access.csv',
        'wizard/product_bundle_wiz.xml',
        'views/product_template_view.xml',
        'views/sale_view.xml',
        'views/stock_picking_view.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
