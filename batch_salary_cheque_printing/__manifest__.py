{
    'name': 'Batch salary JV',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'description': """ 
        Batch salary JV""",
    'author': 'NITS',
    'website': 'https://www.navabrindsol.com/',
    'depends': [
        'base',
        'account',
        'account_accountant',
        'hr_payroll',
    ],
    'data': [
        'reports/batch_jv_bank_advice_template.xml',
        'reports/batch_jv_cheque.xml',
        'reports/batch_jv_template.xml',
        'reports/batch_jv_advice.xml',
        'data/batch_sequence.xml',
        'data/mail_template.xml',
        'security/ir.model.access.csv',
        'views/batch_jv.xml',
    ],
    'license': 'LGPL-3',

}
