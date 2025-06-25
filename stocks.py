from flask import Flask, render_template, request, make_response, url_for, send_from_directory
from datetime import date, timedelta
from urllib.request import urlopen
from urllib.parse import quote_plus
import json
import dateutil.parser
import hashlib
import os

app = Flask(__name__)

def get_icon(change):
    if change == "N/A":
        return None
    else:
        change = float(change[:-1])
        
    if change >= 5:
        icon = '2.png'
    elif change > 0:
        icon = '1.png'
    elif change > -5:
        icon = 'neg1.png'
    else:
        icon = 'neg2.png'
    return icon


def get_quotes(symbols):
    data = []
    base_url = 'https://download.finance.yahoo.com/d/quotes.csv?s='
    query = '+'.join(quote_plus(s.strip()) for s in symbols)
    url = f"{base_url}{query}&f=sl1p2"

    try:
        with urlopen(url) as f:
            rows = f.readlines()
    except Exception:
        return data

    for r in rows:
        values = [x for x in r.decode('utf-8').split(',')]
        symbol = values[0][1:-1]
        try:
            price = float(values[1])
        except ValueError:
            price = 0.0
        change = values[2].strip()[1:-1]
        data.append([symbol, price, change, get_icon(change)])
    return data


def etag(stocks):
    etag_date = date.today()
    if etag_date.isoweekday() > 5:
        etag_date = etag_date - timedelta(days=(etag_date.isoweekday()-5))
    return hashlib.sha224(stocks + etag_date.strftime('%d%m%Y')).hexdigest()

@app.route("/edition/")
def edition():
    stocks = None
    if request.args.get('test', False):
        stocks = "GOOG,LKJLJ"
    elif request.args.get('stocks', False):
        stocks = request.args['stocks']
    else:
        return ("Required params missing", 400)

    data = get_quotes(stocks.split(","))
    response = make_response(render_template('stocks.html', quotes=data))
    response.headers['ETag'] = etag(stocks)
    return response


@app.route("/sample/")
def sample():
    data = get_quotes("GOOG,EPO.L,TSLA,YHOO".split(","))
    response = make_response(render_template('stocks.html', quotes=data))
    response.headers['ETag'] = hashlib.sha224(date.today().strftime('%d%m%Y')).hexdigest()
    return response


@app.route("/validate_config/", methods=['GET', 'POST'])
def validate_config():
    json_response = {'errors': [], 'valid': True}
    try:
        user_settings = json.loads(request.values.get('config', '{}'))
    except ValueError:
        json_response['valid'] = False
        json_response['errors'].append('Invalid JSON supplied')
        user_settings = {}

    if not user_settings.get('stocks', None):
        json_response['valid'] = False
        json_response['errors'].append('Please provide some stock tickers')
    
    response = make_response(json.dumps(json_response))
    response.mimetype = 'application/json'
    return response


@app.route('/meta.json')
def meta_json():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'meta.json', mimetype='application/json')


@app.route('/icon.png')
def icon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'icon.png', mimetype='image/png')
                                       

if __name__ == "__main__":
    debug = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.debug = debug
    app.run(host='0.0.0.0')
