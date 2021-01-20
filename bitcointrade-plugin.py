# -*- coding: utf-8 -*-
'''
BitcoinTrade Python2.7
exchange.rpc = function(path, obj) {
    return exchange.IO("api","POST", path, "obj="+escape(JSON.stringify(obj)));
}
function main() {
	Log(exchange.rpc("/transfer", {cmd: "transfer/assets", body: {select:1}}));
}
'''
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import urllib
import urllib2
import time
import hmac
import hashlib
import random
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

def httpGet(url):
    headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
    req = urllib2.Request(url,headers=headers)
    response = urllib2.urlopen(req)
    return json.loads(response.read())

def getsign(data,secret):
    result = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.md5).hexdigest()
    return result

def httpPostWithSign(url, cmds, api_key):
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6',
        'x-api-key':api_key
        }
    s_cmds = json.dumps(cmds)
    req = urllib2.Request(url, urllib.urlencode({'cmds': s_cmds}), headers=headers)
    req.get_method = lambda: 'DELETE' 
    response = urllib2.urlopen(req)
    return json.loads(response.read())

class MyExchange:

    trade_url = "https://api.bitcointrade.com.br/v3"
    @staticmethod
    def CancelOrder(api_key, orders_id):
        url = MyExchange.trade_url + "/market/user_orders"
        cmds = [{
                'body':{'id':orders_id}
                }]
        raw_data = httpPostWithSign(url, cmds, api_key)
        if 'error' in raw_data.keys():
            return {'error':json.dumps(raw_data['error'],encoding="utf8", ensure_ascii=False)}
        ret_data = {"data":True}
        try:
            result = raw_data['result'].encode('utf8')
        except:
            ret_data = {"data":False}
        ret_data['raw'] = raw_data
        return ret_data
    @staticmethod
    def GetOrder(api_key, api_secret, orders_id):
        url = MyExchange.trade_url + "/orderpending"
        cmds = [{
                'cmd':"orderpending/order",
                'index': random.randint(0,2000), 
                'body':{'id':orders_id}
                }]
        raw_data = httpPostWithSign(url, cmds, api_key, api_secret)
        if 'error' in raw_data.keys():
            return {'error':json.dumps(raw_data['error'],encoding="utf8", ensure_ascii=False)}
        status = 'open'
        if not raw_data['result'][0]['result']:
            return {"error":'Id not found'}
        if int(raw_data['result'][0]['result']['status'])==3:
            status = 'closed'
        if int(raw_data['result'][0]['result']['status'])==5:
            status = 'canceled'
        ret_data = { 
                    "data": {
                        "id": raw_data['result'][0]['result']['id'],
                        "amount": raw_data['result'][0]['result']['amount'],
                        "price": raw_data['result'][0]['result']['price'],
                        "status": status,
                        "deal_amount": raw_data['result'][0]['result']['deal_amount'],
                        "type": "buy" if raw_data['result'][0]['result']['order_side']==1 else "sell", 
                        "avg_price": 0,
                    }
                }
        ret_data['raw'] = raw_data
        return ret_data
    @staticmethod
    def GetOrders(api_key, api_secret, pair):
        url = MyExchange.trade_url + "/orderpending"
        cmds = [{
                'cmd':"orderpending/orderPendingList",
                'body':{
                    'pair':pair, 
                    'page':1, 
                    'size':50
                    }
                }]
        raw_data = httpPostWithSign(url, cmds, api_key, api_secret)
        if 'error' in raw_data.keys():
            return {'error':json.dumps(raw_data['error'],encoding="utf8", ensure_ascii=False)}
        ret_data = {"data":[]}
        for order in raw_data["result"][0]["result"]["items"]:
            status = 'open'
            if int(order['status'])==3:
                status = 'closed'
            if int(order['status'])==5:
                status = 'canceled'
            ret_data["data"].append(
                {
                    "id": order['id'],
                    "amount": order['amount'],
                    "price": order['price'],
                    "status": status,
                    "deal_amount": order['deal_amount'],
                    "type": "buy" if order['order_side']==1 else "sell", 
                }
            )
        ret_data['raw'] = raw_data
        return ret_data
    @staticmethod
    def IO(api_key, path, params):
        url = MyExchange.trade_url + path
        cmds = [json.loads(str(urllib.unquote(params['obj'])))]
        raw_data = httpPostWithSign(url, cmds, api_key)
        if 'error' in raw_data.keys():
            return {'error':json.dumps(raw_data['error'],encoding="utf8", ensure_ascii=False)}
        return {"data":raw_data}

class Server(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    def do_POST(self):

        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        data =json.loads(self.data_string.replace("'", '"'))
        sent_data = {}
        if data['method'] == "cancel":
            access_key = data["access_key"]
            orders_id = data['params']['id']
            sent_data = MyExchange.CancelOrder(access_key, orders_id)
        elif data['method'] == "order":
            access_key = data["access_key"]
            secret_key = data["secret_key"]
            orders_id = data['params']['id']
            sent_data = MyExchange.GetOrder(access_key, secret_key, orders_id)
        elif data['method'] == "orders":
            access_key = data["access_key"]
            secret_key = data["secret_key"]
            pair = data['params']['symbol'].upper()
            sent_data = MyExchange.GetOrders(access_key, secret_key, pair)
        elif data['method'][:2] == "__":
            access_key = data["access_key"]
            path = data["method"].split('_')[-1]
            params = data["params"]
            sent_data = MyExchange.IO(access_key, path, params)

        self.do_HEAD()
        self.wfile.write(json.dumps(sent_data))
        
def run(server_class=HTTPServer, handler_class=Server, port=6667):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting http server...'
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
