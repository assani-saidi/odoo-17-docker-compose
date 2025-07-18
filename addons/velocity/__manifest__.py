# -*- coding: utf-8 -*-
{
    'name': "velocity",
    'summary': """
        Velocity transport customisations""",
    'description': """
        Velocity transport customisations
    """,
    'author': "Assani Saidi",
    'website': "https://github.com/assani-saidi",
    'category': 'Productivity',
    'version': '0.1',
    'depends': ['base', 'project', 'hr', 'fleet', 'account', 'uom', 'account_reports'],
    'license': 'OEEL-1',
    'data': [
        "security/ir.model.access.csv",
        # data
        "data/services.xml",
        "data/paperformats.xml",
        "data/report_action.xml",
        "data/plans.xml",
        "data/parameters.xml",
        "data/sequences.xml",
        # views
        "views/contact.xml",
        "views/project.xml",
        "views/fleet.xml",
        "views/account.xml",
        "views/invoice.xml",
        "views/company.xml",
        "views/project_accessories.xml",
        "views/employee.xml",
        # templates
        "templates/invoice.xml",
        "templates/minimal_layout.xml",
        "data/defaults.xml", # data loaded after views
        # accounting reports
        "reports/general_ledger.xml",
        "reports/partner_ledger.xml"
    ],
    'assets': {
        'web.assets_backend': [
            'velocity/static/src/js/button.css',
        ]
    },
}
