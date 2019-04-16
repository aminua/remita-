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
    def pay_rrr(self, **post):
        form_values, error = {}, {'error_message': []}
        if request.httprequest.method == 'POST':
            if post:
                payload = {
                    "serviceTypeId": post.get('serviceTypeId'),
                    "amount": post.get("totalAmount"),
                    "orderId": post.get("orderId"),
                    "payerName": post.get("payerName"),
                    "payerEmail": post.get("payerEmail"),
                    "payerPhone": post.get("payerPhone"),
                    "description": "Payment for Donation"
                }
                url = 'https://remitademo.net/remita/exapp/api/v1/send/api/echannelsvc/merchant/api/paymentinit'
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
                            """formaction = "https://remitademo.net/remita/ecomm/finalize.reg"
                            name = "merchantId"
                            name = "hash"
                            name = "rrr"
                            name = "responseurl"
                            """
                            rrr = response.get('RRR')
                            hash_string = post.get('merchantId') + rrr + post.get('apiKey')
                            api_hash = hashlib.sha512(hash_string).hexdigest()
                            form_values.update({
                                'form_action': "https://remitademo.net/remita/ecomm/finalize.reg",  # Get the form action from the acquirer config.
                                'merchant_id': post.get('merchantId'),  # get the merchant Id from the post object above
                                'hash': api_hash,  # use the api hash generated above
                                'rrr': response.get('RRR'),  # get RRR from the response from the api endpoint
                                'response_url': "http://localhost:8069/payment/remita/return"  # get the response url
                            })
                    else:
                        response = response.json()
                        error['error_message'].append(response.get('status') + ": " + response.get('statusMessage'))
        return request.render('payment_remita.pay_rrr', dict(form_values=form_values, error=error))  # render the form for rrr payment

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

        data = request.env['payment.transaction']._get_transaction_status(post)

        request.env['payment.transaction'].sudo().form_feedback(data, 'remita')
        return werkzeug.utils.redirect('/shop/payment/validate')
