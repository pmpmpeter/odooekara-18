{
    'name': 'Res Partner Extended for Ekara',
    'category': 'Partner',
    'author': "NITS",
    'website': "www.navabrindsol.com",
    'version': '18.0.1.0.0',
    'description': "Res Partner Extended and Contact Creation Functionality for Ekara",
    'depends': [
        'base',
        'contacts',
        'account',
        'sale',
        'purchase',
    ],
    'data': [
        "security/security.xml",
        "data/ir_cron.xml",
        "data/sequence.xml",
        "data/mail_template.xml",
        "security/ir.model.access.csv",
        "views/contact_creation.xml",
        "views/res_company.xml",
        "views/res_partner.xml",        
    ],
    'installable': True,
    'application': True,
    'auto_install': False,

}
