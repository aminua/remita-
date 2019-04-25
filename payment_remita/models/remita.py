# -*- coding: utf-8 -*-
import hashlib
import logging
import urlparse
import requests

import calendar
import time

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class AcquirerRemita(models.Model):
    _inherit = 'payment.acquirer'

    def _get_remita_urls(self, environment):
        """remita URLs"""
        if environment == 'prod':
            return {
                'remita_get_rrr': "/get_rrr/remita",
                'remita_payment_init': "https://remita.net/remita/exapp/api/v1/send/api/echannelsvc/merchant/api/paymentinit",
                'remita_pay_rrr': "https://remita.net/remita/ecomm/finalize.reg",
                'remita_payment_status': "https://remita.net/remita/ecomm/{merchantId}/{OrderID}/{hash}/orderstatus.reg",
            }
        else:
            return {
                'remita_get_rrr': "/get_rrr/remita",
                'remita_payment_init': "https://remitademo.net/remita/exapp/api/v1/send/api/echannelsvc/merchant/api/paymentinit",
                'remita_pay_rrr': "https://remitademo.net/remita/ecomm/finalize.reg",
                'remita_payment_status': "https://remitademo.net/remita/ecomm/{merchantId}/{OrderID}/{hash}/orderstatus.reg",
            }

    provider = fields.Selection(selection_add=[('remita', "Remita")])
    merchant_id = fields.Char('Merchant Id')
    service_type_id = fields.Char('service Type Id')
    api_key = fields.Char('API KEY')

    def _remita_generate_digital_sign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (odoo contacting remita) or 'out' (remita
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.provider == 'remita'

        if inout == 'in':
            keys = "merchant_id service_type_id order_id total_amount response_url api_key".split(" ")
            sign = ''.join('%s' % (values.get(k)) for k in keys)
        else:
            keys = "product_id pay_item_id webpay_mac_key"
            sign = ''.join('%s' % (values.get(k, '')) for k in keys)
        shasign = hashlib.sha512(sign).hexdigest()
        return shasign

    def remita_form_generate_values(self, values=None):
        if not values:
            values = {}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        acquirer = self
        if not isinstance(values, dict):
            values = dict(values)
        remita_values = {
            'txn_ref':  values['reference'] + "@" + str(calendar.timegm(time.gmtime())),
            'merchant_id': acquirer.merchant_id,
            'service_type_id': acquirer.service_type_id,
            'total_amount': '%d' % int(float_round(values['amount'], 2)),
            'response_url': '%s' % urlparse.urljoin(base_url, '/payment/remita/return'),
            'api_key': acquirer.api_key,
            'remita_init_url': self.remita_get_init_url() or "https://remitademo.net/remita/exapp/api/v1/send/api/echannelsvc/merchant/api/paymentinit",
            'remita_pay_url': self.remita_get_payment_url() or "https://remitademo.net/remita/ecomm/finalize.reg"
        }
        shasign = self._remita_generate_digital_sign(acquirer, 'in', remita_values)
        remita_values['SHASIGN'] = shasign
        values.update(remita_values)
        return values

    def remita_get_form_action_url(self):
        acquirer = self
        return self._get_remita_urls(acquirer.environment)['remita_get_rrr']

    def remita_get_init_url(self):
        acquirer = self
        return self._get_remita_urls(acquirer.environment)['remita_payment_init']

    def remita_get_payment_url(self):
        return self._get_remita_urls(self.environment)['remita_pay_rrr']

    def remita_get_status_url(self):
        return self._get_remita_urls(self.environment)['remita_payment_status']


class TxRemita(models.Model):
    _inherit = 'payment.transaction'

    # Remita status
    _buckaroo_valid_tx_status = ['00', '01']
    _buckaroo_pending_tx_status = ['021', '020', '025', '040']
    _buckaroo_cancel_tx_status = ['012', '61']
    _buckaroo_error_tx_status = ['022', '02', '022', '023', '031', '032', '19', '20', '26', '27']
    _buckaroo_reject_tx_status = ['030', '999']

    remita_txnid = fields.Char('Remita Retrieval Reference')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _remita_form_get_tx_from_data(self, data):
        data_ref = data.get('orderID')
        data_ref = data_ref.split("@")[0]
        reference = data_ref
        if not reference:
            error_msg = 'Remita: received data with missing reference (%s)' % reference
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx_ids = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Remita: received data for reference %s' % reference
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx_ids

    @api.multi
    def _remita_form_validate(self, data):
        status = data.get('status')
        transaction_status = {
            'success': {
                'state': 'done',
                'acquirer_reference': data.get('remita'),
                'date_validate': fields.Datetime.now(),
                'remita_txnid': data.get('RRR')
            },
            'pending': {
                'state': 'pending',
                'acquirer_reference': data.get('remita'),
                'date_validate': fields.Datetime.now(),
                'remita_txnid': data.get('RRR')
            },
            'failure': {
                'state': 'cancel',
                'acquirer_reference': data.get('remita'),
                'date_validate': fields.Datetime.now(),
                'remita_txnid': data.get('RRR')
            },
            'error': {
                'state': 'error',
                'state_message': data.get('error_Message') or _('Remita: feedback error'),
                'acquirer_reference': data.get('remita'),
                'date_validate': fields.Datetime.now(),
                'remita_txnid': data.get('RRR')
            }
        }
        vals = transaction_status.get(status, False)
        if not vals:
            vals = transaction_status['error']
            _logger.info(vals['state_message'])
        return self.write(vals)

    @api.multi
    def _get_transaction_status(self, data, acquirer=None):

        """Return the transaction status for OrderId or RRR returned from Remita payment page.

        ...
        With the response from the get request to status check endpoint, compute the status of a particular transaction
        and return the right status

        """
        rrr = str(data.get('RRR'))
        # TDE: Get params from the configuration
        acquirer = self.env['payment.acquirer'].search([('provider', '=', str(acquirer))], limit=1)
        merchantId = acquirer.merchant_id
        apiKey = acquirer.api_key
        method_get_status = '%_get_status_url' % acquirer.provider
        # -----------------------------------------------------------------
        hash_str = hashlib.sha512(rrr + apiKey + merchantId).hexdigest()
        get_status_url = method_get_status()
        # get_status_url = "https://remitademo.net/remita/ecomm/%s/%s/%s/status.reg" % (merchantId, rrr, hash_str)
        get_status_url = get_status_url % (merchantId, rrr, hash_str)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "remitaConsumerKey=" + merchantId + ",remitaConsumerToken=" + hash_str
        }
        response = requests.get(get_status_url, headers=headers)
        response = response.json()
        if response.get('status') in self._buckaroo_valid_tx_status:
            data.update({
                'status': 'success',
                'remita': 'Remita'
            })
        if response.get('status') in self._buckaroo_reject_tx_status:
            data.update({
                'status': 'failure',
                'remita': 'Remita'
            })
        if response.get('status') in self._buckaroo_error_tx_status:
            data.update({
                'status': 'error',
                'remita': 'Remita'
            })
        if response.get('status') in self._buckaroo_pending_tx_status:
            data.update({
                'status': 'pending',
                'remita': 'Remita'
            })
        return data
