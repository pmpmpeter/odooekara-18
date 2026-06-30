{
    'name': 'Document Workflow Management',
    'version': '18.0.1.0.0',
    'category': 'Documents/Workflow',
    'summary': 'Manages document requests, approvals, and workflow states.',
    'author': 'ekara',
    'depends': ['base','mail'],
    'data': [
        'security/document_security.xml',
        'security/ir.model.access.csv',
        'views/document_views.xml',
    ],
    'installable': True,
    'application': True,
}
