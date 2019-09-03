{
    'name': "Payment Voucher",
    'author': "Olalekan Babawale",
    'description': """
Payment Voucher Report
======================
Payment voucher report. This report is comprehensive enough.
Features:
- Payment Voucher
    """,
    'summary': "Print major receipts including sales receipts",
    'version': "1.0",
    'installable': True,
    'auto_install': False,
    'depends': [
        'account_voucher',
    ],
    'data': [
        'reports/payment_templates.xml',
    ],
}