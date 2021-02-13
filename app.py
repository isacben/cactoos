import xmlrpc.client
import json
import requests
from os import environ
from flask import Flask, render_template, request, make_response
from flask_cors import CORS, cross_origin
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app, resources={r"/upsells": {"origins": "*"}}, supports_credentials=True)

app.config['ODOO_URL'] = environ.get('ODOO_URL')
app.config['ODOO_DB'] = environ.get('ODOO_DB')
app.config['CORS_HEADERS'] = 'Content-Type'

#@app.route('/')
#def hello():
#    return render_template('index.html')

@app.route('/upsells', methods=['POST'])
def index():
    errors = []
    results = {}

    if request.method == "POST":
        
        # get user and password
        try:
            req = request.get_json()

            # Odoo API (PROD)
            URL = app.config['ODOO_URL']
            DB = app.config['ODOO_DB']
            ODOO_USR = req['user']
            ODOO_PWD = req['password']
            tri = req['tri']

            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
            uid = common.authenticate(DB, ODOO_USR, ODOO_PWD, {})

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))

            subscriptions = models.execute_kw(DB, uid, ODOO_PWD, 'sale.subscription', 'search_read', 
                                    [[
                                        '&',
                                        ['user_id', 'ilike', tri + ')'],
                                        '|',
                                        ['upsell_date', '!=', False], ['upsell_order_id', '!=', False],
                                        
                                    ]],
                                    {'fields': ['code', 'partner_id', 'enterprise_final_customer_id', 'referrer_id', 'user_id', 'upsell_date', 'upsell_order_id'],
                                    'limit': 200})

            upsell_orders = [subscription['upsell_order_id'][0] for subscription in subscriptions if subscription['upsell_order_id'] != False]

            orders = models.execute_kw(DB, uid, ODOO_PWD, 'sale.order', 'read', 
                                    [upsell_orders],
                                    {'fields': ['user_id', 'amount_total', 'access_url', 'access_token', 'state']}
                                    )

            for subscription in subscriptions:
                if subscription['upsell_order_id'] != False:
                    order = [o for o in orders if o['id'] == subscription['upsell_order_id'][0]]

                    subscription['o_id'] = order[0].get('id')
                    subscription['o_amount_total'] = order[0].get('amount_total')
                    subscription['o_user_id'] = order[0].get('user_id')
                    subscription['o_access_url'] = order[0].get('access_url')
                    subscription['o_access_token'] = order[0].get('access_token')
                    subscription['o_state'] = order[0].get('state')
            
            results = json.dumps(subscriptions)
            return make_response(results, 200)

            #app.logger.info(subscriptions)
            #app.logger.info(password)
        except:
            return json.dumps({'error': 'Something went wrong! :('}), 400, {'ContentType':'application/json'}
    


if __name__ == '__main__':
    app.run()