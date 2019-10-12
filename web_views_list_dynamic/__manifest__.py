# -*- coding: utf-8 -*-
{
    'name': 'web views list dynamic',
    'description': u'动态列表显示',
    'version': '12.0.1.0',
    'category': 'Website',
    'author': '1di0t',
    'maintainer': 'dgqcjx@gmail.com',

    'depends': [
        'base',
    ],
    'application': False,
    'installable': True,
    'data': [
        "views/base.xml"
    ],
    'qweb': ['static/src/xml/*.xml'],
}