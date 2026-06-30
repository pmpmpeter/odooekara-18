{
    'name': "HR Expense Extended",

    'description': """
        HR Expense Extended Functionality for Ekara
        
    """,
    'category': 'HR',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'mail',
        'multi_level_approval_configuration',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/payment_approval_config.xml',
        'views/payment_approval.xml',
        'views/payment_approval_report.xml',
        'data/mail_template.xml',
        'views/menu.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
