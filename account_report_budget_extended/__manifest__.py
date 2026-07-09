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
    'depends': ['account_reports','account_budget'],
    'data': [
    	'security/ir.model.access.csv',
    	'security/res_groups.xml',
    	'data/ir_sequence.xml',
    	'views/account_report_budget_views.xml',
    	'views/fund_management_views.xml',
    	'views/budget_analytic_views.xml',
    	'views/cash_management_views.xml',
    	'views/crr_budget_views.xml',
    	'views/budget_department_views.xml',
    	'views/menu.xml'
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
   
   
}
