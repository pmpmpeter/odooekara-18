{
    'name': 'Ekara PDF',
    'version': '18.0.1.0.0',
    'summary': 'Ekara PDF Reort module created by Rajashree',
    'author': 'Rajashree',
    'category': 'Custom',
    'depends': ['base', 'account'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'wizard/pdf_report.xml',
        'report/pdf_report_action.xml',
        'report/pdf_report_template.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
}
