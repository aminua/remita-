from odoo import api, models
from odoo.tools.misc import formatLang


class payment_voucher_report(models.AbstractModel):
    _name = 'report.payment_voucher.voucher_report_account'

    def convert(self, amount, cur):
        return amount_to_text_en.amount_to_text(amount, 'en', cur)

    def get_amount_lines(self, o):
        amount = 0.00
        if o.line_ids:
            for line in o.line_ids:
                amount += line.price_subtotal
        else:
            for line in o.line_ids:
                amount += line.price_subtotal
        return amount

    def get_lines(self, communication=''):
        invoice = ''
        if communication:
            invoice = self.env['account.invoice'].search([('number', '=', communication)])
        if invoice:
            return invoice.invoice_line_ids
        return []

    @api.multi
    def formated_amount(self, amount, currency_obj=None):
        amount = formatLang(self.env, amount,
                            currency_obj=currency_obj if currency_obj else self.env.user.company_id.currency_id)
        return amount

    def get_amount_in_words(self, o, amount):
        return o.amt2words(amount)

    @api.model
    def render_html(self, docids, data=None):
        account_voucher = self.env['account.payment'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': account_voucher,
            'data': data,
            'convert': self.convert,
            'get_amount_lines': self.get_amount_lines,
            'formated_amount': self.formated_amount,
            'get_lines': self.get_lines,
            'remove_format': self.remove_currency_formatting,
            'get_amount_in_words': self.get_amount_in_words,
        }
        return self.env['report'].render('payment_voucher.voucher_report_account', docargs)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
