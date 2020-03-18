# -*- encoding: utf-8 -*-
{
    'name': "Route network maps",
    'version': '12.0.0',
    'summary': 'Route network maps',
    'description': """Route network maps""",
    'author': '1di0t',
    "depends": ['base', 'stock', 'route_network', 'web'],
    'data': [
        'views/route_network_maps.xml',
        'static/xml/base.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
