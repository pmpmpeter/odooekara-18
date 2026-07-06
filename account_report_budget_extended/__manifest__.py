# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accounting Reports Budgeting - Extended',
    'summary': 'View and create reports',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_reports'],
    'data': [
    	'views/account_report_budget_views.xml'   
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
   
   
}
