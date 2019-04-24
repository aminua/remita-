from num2words import num2words
from odoo import api, models
from odoo.tools.misc import formatLang


class print_payment_report(models.AbstractModel):
    _name = 'report.dev_print_receipt.print_payment_id'

    def amt2words(self, amount, currency_id, precision=2):
        currency = str(currency_id.currency_word)
        change_amt = (amount - int(amount)) * pow(10, precision)
        words = '{main_amt} {main_word}'.format(
            main_amt=num2words(int(amount)),
            main_word=currency,
        )
        if change_amt > 0:
            subunits = [subunit.name for subunit in currency_id.subunit_ids]
            change = subunits[0] if subunits else ''
            words += ' and {change_amt} {change_word}'.format(
                change_amt=num2words(int(change_amt)),
                change_word=change,
            )
        words_list = words.strip().split(' ')
        words_list = map(lambda word: self.format_word(word), words_list)
        return ' '.join(words_list)

    def format_word(self, word):
        if word == 'and':
            return word
        if word == 'False':
            return ''
        return word.capitalize()

    def get_description(self, partner_id, partner_type, communication=''):
        if not communication:
            return str("Payment {action} {partner}".format(action='received from' if partner_type == 'customer' else 'to',
                                                                partner=partner_id.name))
        return communication

    def get_products(self, communication=''):
        if not (communication or isinstance(communication, str)):
            return False
        invoice_obj = self.env['account.invoice'].search([('number', '=', communication)], limit=1)
        for line in invoice_obj.invoice_line_ids:
            if line.product_id:
                return True
        return False

    def fetch_products(self, communication=''):
        if self.get_products(communication):
            invoice = self.env['account.invoice'].search([('number', '=', communication)], limit=1)
            products = [line.product_id.name for line in invoice.invoice_line_ids]
            return products
        return []

    @api.multi
    def format_amount(self, amount, currency_obj=None):
        if currency_obj is None:
            currency_obj = self.get_default_currency()
        amount = formatLang(self.env, amount, currency_obj=currency_obj)
        return amount

    def get_default_currency(self):
        return self.env.user.company_id.currency_id

    @api.model
    def render_html(self, docids, data=None):
        account_payment = self.env['account.payment'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': account_payment,
            'amt2words': self.amt2words,
            'format_amount': self.format_amount,
            'get_description': self.get_description,
            'get_products': self.get_products,
            'currency_id': self.get_default_currency,
            'fetch_products': self.fetch_products,
            'data': data,
        }
        return self.env['report'].render('payment_voucher.voucher_report_account', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: