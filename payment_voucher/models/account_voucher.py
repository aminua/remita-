from odoo import models, fields, api, _
from num2words import num2words

# TDE: write conversion to words in function outside the classes


def capitalize_word(words):
    if words is not False or None:
        return ' '.join(word.capitalize() for word in words.split(' '))


class account_voucher(models.Model):
    _inherit = "account.voucher"

    check_amount = fields.Char(string="Amount in Words", compute="_get_amount_in_words")

    @api.onchange('amount')
    def _onchange_amount(self):
        self.check_amount = self.amt2words(amount=self.amount,
                                           currency=self.currency_id.currency_word if self.currency_id else
                                           self.company_id.currency_id.currency_word,
                                           change=((lambda model, domain, limit=None: self.env[model].search(domain,
                                                                                                             limit=limit))(
                                               'res.currency.subunit', [], limit=1)).name)

    def amt2words(self, amount, currency='dollars', change='cents', precision=2):
        change_amt = self.get_change_amount(amount, precision)
        words = '{main_amt} {main_word}'.format(
            main_amt=capitalize_word(num2words(int(amount))),
            main_word=capitalize_word(currency),
        )
        if change_amt > 0:
            words += ' and {change_amt} {change_word}'.format(
                change_amt=capitalize_word(num2words(int(change_amt))),
                change_word=capitalize_word(change),
            )
        return words

    def get_change_amount(self, amount, precision=2):
        return int(round((amount - int(amount)) * pow(10, precision)))

    def get_main_amount(self, amount):
        return int(amount)

    @api.one
    @api.depends('amount')
    def _get_amount_in_words(self):
        self.check_amount = self.amt2words(
            self.amount,
            self.currency_id.currency_word or self.company_id.currency_id.currency_word,
            ((lambda model, domain, limit=None: self.env[model].search(domain, limit=limit)('res.currency.subunit',
                                                                                            [('currency_id', '=',
                                                                                              self.currency_id.id)],
                                                                                            limit=1).name))
        )


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    amount_in_words = fields.Char("Amount in Words", compute="_get_amount_in_words")

    @api.onchange('amount')
    def _onchange_amount(self):
        self.check_amount = self.amt2words(amount=self.amount,
                                           currency=self.currency_id.currency_word if self.currency_id else
                                           self.company_id.currency_id.currency_word,
                                           change=((lambda model, domain, limit=None: self.env[model].search(domain,
                                                                                                             limit=limit))(
                                               'res.currency.subunit', [], limit=1)).name)

    def amt2words(self, amount, currency='dollars', change='cents', precision=2):
        change_amt = self.get_change_amount(amount, precision)
        words = '{main_amt} {main_word}'.format(
            main_amt=capitalize_word(num2words(int(amount))),
            main_word=capitalize_word(currency),
        )
        if change_amt > 0:
            words += ' and {change_amt} {change_word}'.format(
                change_amt=capitalize_word(num2words(int(change_amt))),
                change_word=capitalize_word(change),
            )
        return words

    def get_change_amount(self, amount, precision=2):
        return int(round((amount - int(amount)) * pow(10, precision)))

    def get_main_amount(self, amount):
        return int(amount)

    @api.one
    @api.depends('amount')
    def _get_amount_in_words(self):
        self.check_amount = self.amt2words(
            self.amount,
            self.currency_id.currency_word or self.company_id.currency_id.currency_word,
            ((lambda model, domain, limit=None: self.env[model].search(domain, limit=limit)('res.currency.subunit',
                                                                                            [('currency_id', '=',
                                                                                              self.currency_id.id)],
                                                                                            limit=1).name))
        )
