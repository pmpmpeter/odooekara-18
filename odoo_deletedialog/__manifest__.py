# -*- coding: utf-8 -*-

{
    'name': 'Delete Dialog Box',
    'category': 'Extra Tools',
    'summary': 'Get a Confirmation dialog box upon deletion of a record',
    'version': '18.0.1.0.0',
    'description': """A Confirmation Pop Up dialog box will show upon deletion of a record/row of item""",
    'author': 'Navabrind IT Solutions',
    'website': 'https://www.navabrindsol.com',
    'sequence': 4,
    'price': 5.0,
    'currency': 'EUR',
    'images':['images/banner_confirmation.png'],
    'depends': ['base','web'],
    'data': [
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'odoo_deletedialog/static/src/js/extra.js',
        ],
    },
	'license': 'AGPL-3'
}
