from odoo import models, fields, api, _
from num2words import num2words


class account_voucher(models.Model):
    _inherit = "account.voucher"

    check_amount = fields.Char(string="Amount in Words", compute="_get_amount_in_words")
    amount = fields.Float(string="Amount")

    @api.onchange('amount')
    def _onchange_amount(self):
        self.check_amount = self.amt2words(amount=self.amount,
                                           currency=self.currency_id.currency_word if self.currency_id else
                                           self.company_id.currency_id.currency_word,
                                           change=((lambda model, domain, limit=None: self.env[model].search(domain,
                                                                                                             limit=limit))(
                                               'res.currency.subunit', [], limit=1)).name)

    def amt2words(self, amount, currency='dollars', change='cents', precision=2):
        change_amt = (amount - int(amount)) * pow(10, precision)
        words = '{main_amt} {main_word}'.format(
            main_amt=num2words(int(amount)),
            main_word=currency,
        )
        if change_amt > 0:
            words += ' and {change_amt} {change_word}'.format(
                change_amt=num2words(int(change_amt)),
                change_word=change,
            )
        return words

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