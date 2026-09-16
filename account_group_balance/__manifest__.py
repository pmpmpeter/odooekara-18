# -*- coding: utf-8 -*-

{
    'name': 'Account Group Balance',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Show consolidated balance for shared accounts across companies',
    'description': """
        Adds a Group Balance smart button to shared accounts.

        The Group Balance shows posted journal item balances for all
        companies associated with the shared account, while preserving
        Odoo's standard company-specific Balance smart button.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_group_balance_line_views.xml',
        'views/account_account_views.xml',
    ],
    'installable': True,
    'application': False,
}