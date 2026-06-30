{
    'name': 'Attendance Form F,T,H',
    'version': '18.0.1.0.0',
    'category': 'HR',
    'depends': ['hr', 'hr_attendance'],
    'data': [

        'security/ir.model.access.csv',
        'wizard/attendance_report_wizard.xml',
        'views/menu.xml',
        'report/form_f.xml',
        'report/form_t.xml',
        'report/form_h.xml',
        'report/hr_compliances.xml',
    ],
    'application': True,
}
