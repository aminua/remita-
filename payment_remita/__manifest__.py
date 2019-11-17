# -*- coding: utf-8 -*-

{
    'name': 'Remita Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Remita Implementation',
    'version': '1.0',
    'description': """Remita Payment Acquirer""",
    'author': 'MgB Computers',
    'depends': ['website', 'payment', 'website_payment', 'website_sale'],
    'data': [
        'views/remita.xml',
        'views/payment_acquirer.xml',
        'data/remita.xml',
        'templates/payment_templates.xml',
    ],
    'installable': True,
}
