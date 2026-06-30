{
    'name': 'Employee Probation',
    'version': '18.0.1.0.0',
    'category': 'HR',
    'summary': 'Employee Probation details',
    'description': """

    """,
    'depends': ['base', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        # 'data/emp_prob_mail_template.xml',
        'data/probation_confirmation_letter.xml',
        'views/emp_probation_view.xml',
        'views/prob_review.xml',
        # 'report/emp_prob_report.xml',
        'report/probation_review_form.xml',

    ],
    'installable': True,
    'license': 'LGPL-3'
}
