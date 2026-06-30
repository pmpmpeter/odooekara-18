{
    'name': "Project Extended",

    'description': """
        Project Extended Functionality for Ekara
        
    """,
    'category': 'Project',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'mail',
        'project_account',
        'hr_extended',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/project_security.xml',
        # 'views/project_project_views.xml',
        'data/mail_template_data.xml',
        'data/project_cron.xml',
        'wizard/project_task_assign_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
