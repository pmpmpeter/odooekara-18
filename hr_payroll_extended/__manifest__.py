{
    'name': 'HR Payroll',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Integrate custom employee fields with the hr_payroll module.',

    'author': 'Your Company',
    'depends': [
        'hr',
        'hr_payroll', 'report_xlsx',
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/payroll_for_the_month.xml',
        'reports/payslip_pdf_format.xml',
        'views/hr_payslip.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
