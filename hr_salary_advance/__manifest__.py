{
    'name': 'Salary Advance',
    'version': '18.0.1.0.0',
    'category': 'HR',
    'description': """ 
        Salary Advance workflow for employees""",
    'author': 'NITS',
    'website': 'https://www.navabrindsol.com/',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'hr_extended',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/hr_job_level.xml',
        'views/hr_contract.xml',
        'views/hr_salary_advance.xml',
        'wizard/hr_salary_advance_reject_wizard.xml',
    ],
    'license': 'LGPL-3',

}
