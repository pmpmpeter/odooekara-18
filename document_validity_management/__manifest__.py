# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Document Validity Management',
    'version': '18.0.1.0.0',
    'summary': 'Document Validity Management',
    'sequence': 10,
    'description': """
        Document Validity Management
    """,
    'category': 'Project',
    'depends': ['project','project_extended'],
    'data': [
        'data/mail_template_data.xml',
        'security/ir.model.access.csv',
        'data/document_type_data.xml',
        'data/ir_cron.xml',
        'views/document_type_views.xml',
        # 'views/documents_share_views.xml',
        # 'views/project_project_views.xml'

    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
