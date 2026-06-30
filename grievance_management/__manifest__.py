# -*- coding: utf-8 -*-
{
    'name': "Employee Grievance Management",

    'summary': "Employee Grievance Management",

    'description': """
Employee Grievance Management
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        'data/sequence.xml',
        'data/grievance_type_demo.xml',
        'data/mail_template.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/employee_grievance.xml',
        'views/hr_employee.xml',
        'views/grievance_type_config.xml',
    ],
}
