try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import werkzeug
import hashlib
import requests
from odoo import _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import odoo.http as http


_logger = logging.getLogger(__name__)


class WebsiteSale(WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sale order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        SaleOrder = request.env['sale.order']

        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        values = {
            'website_sale_order': order
        }

        values['errors'] = SaleOrder._get_errors(order)
        values.update(SaleOrder._get_website_data(order))
        if not values['errors']:
            acquirers = request.env['payment.acquirer'].search(
                [('website_published', '=', True), ('company_id', '=', order.company_id.id)]
            )
            values['acquirers'] = []
            for acquirer in acquirers:
                assert isinstance(order, object)
                acquirer_button = acquirer.with_context(submit_class='btn btn-primary', submit_txt=_('Pay Now')).sudo().render(
                    order.name,
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    values={
                        'return_url': '/shop/payment/validate',
                        'partner_id': shipping_partner_id,
                        'billing_partner_id': order.partner_invoice_id.id,
                    }
                )
                acquirer.button = acquirer_button
                values['acquirers'].append(acquirer)

            values['tokens'] = request.env['payment.token'].search([('partner_id', '=', order.partner_id.id), ('acquirer_id', 'in', acquirers.ids)])

        return request.render("website_sale.payment", values)


class RemitaPayment(http.Controller):
    # Pay with RRR using this controller
    @http.route('/get_rrr/remita', type="http", auth='public', website=True)
    def get_rrr(self, **post):
        form_values, error = {}, {'error_message': []}
        if post:
            payload = {
                "serviceTypeId": str(post.get('serviceTypeId')),
                "amount": str(post.get("totalAmount")),
                "orderId": str(post.get("orderId")),
                "payerName": str(post.get("payerName")),
                "payerEmail": str(post.get("payerEmail")),
                "payerPhone": str(post.get("payerPhone")),
                "description": str(post.get("orderId"))
            }
            url = str(post.get('remita_init_url'))
            hash_string = post.get('merchantId') + post.get('serviceTypeId') + post.get('orderId') + post.get('totalAmount') + post.get('apiKey')
            api_hash = hashlib.sha512(hash_string).hexdigest()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': "remitaConsumerKey=" + post.get('merchantId') + ",remitaConsumerToken=" + api_hash
            }
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            if response.status_code == 200:
                try:
                    response.json()
                except Exception:
                    response_json = response.content.split("(", 1)[1].strip(")")  # convert to json
                    response = json.loads(response_json)
                    if response.get('statuscode') and response.get('statuscode') == '025':
                        rrr = response.get('RRR')
                        hash_string = post.get('merchantId') + rrr + post.get('apiKey')
                        api_hash = hashlib.sha512(hash_string).hexdigest()
                        form_action = str(post.get('remita_pay_url'))
                        merchant_id = str(post.get('merchantId'))
                        rrr = str(response.get('RRR'))
                        response_url = str(post.get('responseurl'))
                        return request.redirect('/pay_rrr/remita?form_action=%s&merchant_id=%s&hash=%s&rrr=%s&response_url=%s' %
                                                (form_action, merchant_id, api_hash, rrr, response_url))
                else:
                    response = response.json()
                    error['error_message'].append(response.get('status') + ": " + response.get('statusMessage'))
        # TDE: Re-write this part of the code to catch any error that may occur.
        return request.render('payment_remita.pay_rrr', dict(form_values=form_values, error=error))  # render the form for rrr payment

    # Pay RRR
    @http.route('/pay_rrr/remita', type='http', auth='public', csrf=False, website=True)
    def pay_rrr(self, **post):
        if request.httprequest.method == "GET":
            values = {}
            if post:
                values['form_action'] = post.get('form_action')
                values['merchant_id'] = post.get('merchant_id')
                values['hash'] = post.get('hash')
                values['rrr'] = post.get('rrr')
                values['response_url'] = post.get('response_url')
            return request.render('payment_remita.pay_rrr', dict(form_values=values))

    # Pay with RRR using this controller
    @http.route(['/payment/remita/return'], type='http', auth='public', csrf=False)
    def payment_feedback(self, **post):

        # ------------------------------------------------------------------------------
        # GET FEEDBACK AFTER PAYMENT ON REMITA PLATFORM
        # ------------------------------------------------------------------------------

        _logger.info('remita payment feedback: entering form_feedback with post data %s', pprint.pformat(post))

        # ---------------------------------------------------------------------------------
        # Query the get transaction status endpoint to get the status of the payment
        # ---------------------------------------------------------------------------------
        post = dict(post)

        data = request.env['payment.transaction']._get_transaction_status(post, acquirer='remita')

        request.env['payment.transaction'].sudo().form_feedback(data, 'remita')
        return werkzeug.utils.redirect('/shop/payment/validate')
