try:
    import simplejson as json
except ImportError:
    import json
import logging
import hashlib
import requests
from string import Template

_logger = logging.getLogger(__name__)

import odoo.addons.web.http as http


class RemitaController(http.Controller):
    _cp_path = '/payment/remita/return/'

    @http.route(['/payment/remita/return/'], type='http', auth="none", methods=['GET', 'POST'])
    def index(self, **post):
        SIMPLE_TEMPLATE = Template("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
            <head>
                <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
                <title>Transaction Status</title>
                <style>
                    #header {
                        background-color:orangered;
                        color:white;
                        text-align:center;
                        padding:2px;
                    }
                    #section {
                        width:350px;
                        margin:0 auto;
                        text-align:center;
                        padding:10px;
                    }
                </style>
            </head>
            <body>
                <div id="header">      
                    <h1>Medical And Dental Council Of Nigeria</h1>
                    <a href="http://198.23.62.95:8069">Back Home</a>
                </div>
                <div id="section">      
                    <h2>Transaction Status</h2>
                </div>
                <div style="width:800px; margin:0 auto; background-color:green; color:white; text-align:center;"> 
                    <h3>Thank You!!!</h3>
                    <p>Your Transaction Was Successful</p>
                    <p>Reason: ${description}</p>
                    <p>orderId: ${orderId}</p>
                    <p>RRR: ${paymentreference}</p>
                    <p>Thank You For Trusting MDCN.</p>
                </div>
            </body>
        </html>
        """)
        SIMPLE_TEMPLATE2 = Template("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html> 
            <head>
                <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
                <title>Transaction Status</title>
                <style>
                    #header {
                        background-color:orange red;
                        color:white;
                        text-align:center;
                        padding:5px;
                    }
                    #section {
                        width:350px;
                        text-align:center;
                        margin:0 auto;
                        padding:10px;
                    }
                </style>
            </head>
            <body>
                <div id="header">
                    <h1>Medical And Dental Council Of Nigeria</h1>
                    <a href="http://198.23.62.95:8069">Back Home</a> 
                </div>
                <div id="section">
                    <h2>Transaction Status</h2>
                </div>
                <div style="width:800px; margin:0 auto; background-color:red; color:white; text-align:center;"> 
                    <h3>Sorry!!!</h3>
                    <p>Your Transaction Was Unsuccessful</p>
                    <p>Reason: ${description}</p>
                    <p>orderId: ${orderId}</p>
                    <p>RRR: ${paymentreference}</p>
                    <p>Thank You For Trusting MDCN.</p>
                </div>
            </body>
        </html>
        """)
        """url = ('https://webpay.interswitchng.com/paydirect/api/v1/gettransaction.json')"""
        url = 'http://www.remitademo.net/remita/ecomm'
        merchantId = '2547916'
        rrr = post.get('RRR')
        api_key = '1946'
        nhash = rrr + api_key + merchantId
        hash_object = hashlib.sha512(nhash)
        hex_dig = hash_object.hexdigest()
        user_agent = "json/status.reg"
        full_url = url + '/' + merchantId + '/' + rrr + '/' + hex_dig + '/' + user_agent
        response = requests.get(full_url)
        result = response.json()
        code = result['status']
        description = result['message']
        paymentreference = result['RRR']
        orderId = result['orderId']
        if code == '01' or code == '00':
            _logger.info('remita: validated data')
            return SIMPLE_TEMPLATE.substitute(dict(description=description,paymentreference=paymentreference,orderId=orderId))
        else:
            _logger.warning('Remita received %s' % description)
            return SIMPLE_TEMPLATE2.substitute(dict(description=description,paymentreference=paymentreference))
