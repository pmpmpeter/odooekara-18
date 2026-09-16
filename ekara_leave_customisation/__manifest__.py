{
    'name': 'Leave Encashment',
    'version': '18.0.1.0',
    'depends': ['hr_holidays','mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/leave_encashment_views.xml',
        'views/hr_employee_views.xml',
        'data/ir_rule.xml',
    ],
    'application': True,
}