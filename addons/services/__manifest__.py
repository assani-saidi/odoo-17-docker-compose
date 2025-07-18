# -*- coding: utf-8 -*-
{
    'name': "Custom Subscription Services",

    'summary': """
        Custom module to manage subscription services""",

    'description': """
        Custom module to manage subscription services
    """,

    'author': "Assani Saidi",
    'website': "https://github.com/assani-saidi",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'web_enterprise'],
    'auto_install': True,
    'installable': True,
    'application': True,

    # always loaded
    'data': [
        'data/system_parameter.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "services/static/src/js/services.js",
            "services/static/src/xml/strip.xml",
            "services/static/src/xml/banner.xml",
            ('replace', 'web_enterprise/static/src/webclient/home_menu/expiration_panel.scss', 'services/static/src/css/expired.scss'),
        ],
    }

}
