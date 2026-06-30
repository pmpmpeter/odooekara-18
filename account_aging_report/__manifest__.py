{
    'name': 'Accounts Extended- Aging Report Based on Invoice Date',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'description': """ 
        Ageing Report Based on Invoice Date""",
    'author': 'NITS',
    'website': 'https://www.navabrindsol.com/',
    'depends': [
        'base',
        'account',
        'account_accountant',
        'account_reports',
    ],
    'data': [
        'report/account_aging.xml',
    ],
    'license': 'LGPL-3',

}
