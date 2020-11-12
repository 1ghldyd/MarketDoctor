from bs4 import BeautifulSoup
import requests

from selenium import webdriver
import schedule
import time

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pymongo import MongoClient
import jwt      # (패키지: PyJWT)
import datetime     # 토큰 만료시간
import bcrypt   # 암호화

from functools import wraps

from urllib.request import HTTPError
import xml.etree.ElementTree as ET

from bokeh.plotting import figure, show, output_file
from bokeh.layouts import gridplot
from bokeh.models.formatters import NumeralTickFormatter
from bokeh.embed import json_item
import json
import pandas as pd

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.marketdoctor

SECRET_KEY = '!r1l1a1x2o2g3k3s3'        # JWT 토큰을 만들 때 필요한 비밀문자열입니다.

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register')
def register():
   return render_template('register.html')

@app.route('/myport-modify')
def myport_modify():
   return render_template('myport.html')


@app.route('/api/register', methods=['POST'])
def api_register():
   id = request.form['id']
   pw = request.form['pw']
   if db.user.find_one({'id': id},{'_id':False}) is not None:
       return jsonify({'result': 'fail', 'msg':'아이디가 중복되었습니다. 다시 입력 해 주세요.'})
   else:
       pw_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
       db.user.insert_one({'id':id,'pw':pw_hash,'email':id,'notice_rate_up':'','notice_rate_down':'','port':[]})
       return jsonify({'result': 'success', 'msg':'회원가입이 완료되었습니다.'})

@app.route('/api/login', methods=['POST'])
def api_login():
   id = request.form['id']
   pw = request.form['pw']
   user_data = db.user.find_one({'id': id},{'_id':False})

   if bcrypt.checkpw(pw.encode('utf-8'), user_data['pw']):
      # JWT 토큰에는, payload와 시크릿키가 필요합니다.
      # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
      # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
      # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
      payload = {
         'id': id,
         'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=60*60*24)   #24시간 유효
      }
      token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
      return jsonify({'result': 'success','token':token})
   else:
      return jsonify({'result': 'fail', 'msg':'아이디/비밀번호가 일치하지 않습니다.'})

@app.route('/api/valid', methods=['GET'])
def api_valid():
    access_token = request.headers.get('token')
    if access_token is not None:
        try:
            jwt.decode(access_token, SECRET_KEY, algorithms=['HS256'])
            return jsonify({'result': 'success','msg':'토큰이 유효합니다.'})
        except jwt.InvalidTokenError:
            return jsonify({'result': 'fail', 'msg': '토큰이 만료되었습니다.'})
    else:
        return jsonify({'result': 'fail', 'msg': '토큰이 없습니다.'})

@app.route('/api/myconfig', methods=['GET'])
def api_myconfig():
    payload = token_payload_read()
    if payload is not None:
        user_data = db.user.find_one({'id': payload['id']}, {'_id': 0})
        return jsonify({'result': 'success', 'payload':{'email': user_data['email'], 'notice_rate_up': user_data['notice_rate_up'], 'notice_rate_down': user_data['notice_rate_down']}})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/myconfig', methods=['POST'])
def myconfig():
    payload = token_payload_read()
    if payload is not None:
        user_data = db.user.find_one({'id': payload['id']}, {'_id': 0})
        db.user.update_one({'id': user_data['id']}, {'$set': {'email': request.form['email'], 'notice_rate_up': request.form['notice_rate_up'].replace('%', ''), 'notice_rate_down': request.form['notice_rate_down'].replace('%', '')}})
        return jsonify({'result': 'success', 'msg': '설정이 저장되었습니다.'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

def token_payload_read():
    access_token = request.headers.get('token')
    if access_token is not None:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.InvalidTokenError:
            return None
    else:
        return None

@app.route('/api/myport-refresh', methods=['GET'])
def myport_refresh():
    payload = token_payload_read()
    if payload is not None:
        user_data = db.user.find_one({'id': payload['id']}, {'_id': 0})
        ports_data = user_data['port']
        if len(ports_data) != 0:
            ports = []
            for port in ports_data:
                port_info = get_stock_cur(port['code'],1)
                ports.append({'code':port['code'], 'name':port['name'], 'current_price':port_info['price'], 'debi':port_info['debi'], 'rate':port_info['rate'], 'volume':port_info['volume']})

            return jsonify({'result': 'success', 'ports_data': ports})
        else:
            return jsonify({'result': 'success_but', 'msg': '등록된 종목이 없습니다.'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/myport-info', methods=['POST'])
def myport_info():
    payload = token_payload_read()
    if payload is not None:
        stock_data = get_stock_info(request.form['code'], 1)
        chart_data = chart(stock_data['stock_data'][0])
        return jsonify({'result': 'success', 'stock_data': stock_data, 'chart_data':chart_data})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

def chart(data):
    '''
    x = [1,2,3,4,5]
    y = [6,7,2,4,5]
    output_file("lines.html")
    p = figure(title="simple line example", x_axis_label="x", y_axis_label="y")
    p.line(x,y,legend="Temp.",line_width=2)
    show(p)
    '''
    df = pd.DataFrame(data, columns=['date','open','high','low','close','volume'])
    #print(df)
    inc = df.close >= df.open
    dec = df.open > df.close

    p_candlechart = figure(plot_width=500, plot_height=200, x_range=(-1, len(df)), tools=['crosshair, hover'])
    p_candlechart.segment(df.index[inc], df.high[inc], df.index[inc], df.low[inc], color="red")
    p_candlechart.segment(df.index[dec], df.high[dec], df.index[dec], df.low[dec], color="blue")
    p_candlechart.vbar(df.index[inc], 0.9, df.open[inc], df.close[dec], fill_color="red", line_color="red")
    p_candlechart.vbar(df.index[dec], 0.9, df.open[dec], df.close[dec], fill_color="blue", line_color="blue")
    p_candlechart.yaxis[0].formatter = NumeralTickFormatter(format='0,0')
    p_candlechart.xaxis.ticker = [0,1,2,3,4,5,6,7,8,9]
    p_candlechart.xaxis.visible = False

    '''
    p_candlechart.hover.tooltips=[
        ("index", "$index"),
        ("(x,y)", "($x, $y)"),
        ("radius", "@radius"),
        ("fill color", "$color[hex, swatch]:fill_color"),
        ("foo", "@foo"),
        ("bar", "@bar"),
        ("date", "$date"),
        ("open", "@open"),
    ]
    '''
    p_volumechart = figure(plot_width=500, plot_height=100, x_range=p_candlechart.x_range, tools=['xpan, crosshair, xwheel_zoom, reset, hover, box_select, save'])
    p_volumechart.vbar(df.index, 0.9, df.volume, fill_color="black", line_color="black")
    major_label = {
        i: date.strftime('%m/%d') for i, date in enumerate(pd.to_datetime(df["date"]))
    }
    major_label.update({len(df):''})
    p_volumechart.xaxis.major_label_overrides = major_label
    p_volumechart.xaxis.ticker = [0,1,2,3,4,5,6,7,8,9]
    #p_volumechart.xaxis.major_label_orientation = 0.5
    p_volumechart.yaxis[0].formatter = NumeralTickFormatter(format='0,0')

    p = gridplot([[p_candlechart], [p_volumechart]], toolbar_location=None)

    #output_file("lines.html")
    #show(p)
    #jsonified_p = json_item(model=p, target="myplot")
    #return json.dumps(jsonified_p, ensure_ascii=False, indent='\t')
    jsonified_p = json_item(model=p, target="myplot")
    return json.dumps(jsonified_p, ensure_ascii=False, indent='\t')
    #script = Markup(script)
    #div = Markup(div)
    #return render_template('plot_template.html', plot1_script=script, plot1_div=div)

@app.route('/api/myport-modify', methods=['GET'])
def myport_read():
    payload = token_payload_read()
    if payload is not None:
        user_data = db.user.find_one({'id': payload['id']}, {'_id': 0})
        ports = user_data['port']
        if len(ports) != 0:
            return jsonify({'result': 'success', 'ports_data': ports})
        else:
            return jsonify({'result': 'success_but', 'msg': '등록된 종목이 없습니다.'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/myport-modify-add', methods=['POST'])
def myport_add():
    user = token_payload_read()
    if user is not None:
        user_data = db.user.find_one({'id': user['id']}, {'_id': 0})
        add_code = request.form['code']

        if any(add_code in code for code in user_data['port']):
            return jsonify({'result': 'success', 'msg': '해당 종목은 이미 등록되어 있습니다!'})
        else:
            port_info = get_stock(add_code)
            user_data['port'].append({'code': add_code, 'name': port_info['name']})
            db.user.update_one({'id': user['id']}, {'$set': {'port': user_data['port']}})
            return jsonify({'result': 'success', 'msg': '종목이 추가되었습니다!'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/myport-modify-del', methods=['POST'])
def myport_del():
    user = token_payload_read()
    if user is not None:
        user_data = db.user.find_one({'id': user['id']})
        delete_code = request.form['code']
        delete_name = request.form['name']
        del user_data['port'][user_data['port'].index({'code': delete_code, 'name': delete_name})]
        db.user.update_one({'id': user['id']}, {'$set': {'port': user_data['port']}})
        return jsonify({'result': 'success', 'msg': '종목이 삭제되었습니다!'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

def get_stock(code):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
    #data = requests.get('https://finance.naver.com/item/main.nhn?code=' + code, headers=headers)
    url = requests.get('https://vip.mk.co.kr/newSt/price/daily.php?stCode=' + code, headers=headers)

    data = url.content.decode('euc-kr','replace')
    soup = BeautifulSoup(data, 'html.parser')

    name = soup.select_one('title').text
    name = name[0:name.find(code)-1]
    #current_price = soup.select_one('#lastTick\[6\] > font.f3_r').text
    #rate = soup.select_one('#disArr\[0\] > span').text

    #return ({'code':code, 'name':name, 'current_price':current_price, 'rate':rate})
    return ({'code':code, 'name':name})

def get_stock_cur(code,try_cnt):
    try:
        temp = requests.get('http://asp1.krx.co.kr/servlet/krx.asp.XMLSiseEng?code=' + code).content
        temp = temp[1:]
        root = ET.fromstring(temp)
        for type_tag in root.findall('TBL_StockInfo'):
            cur_juka = int(type_tag.get('CurJuka').replace(',', ''))
            prev_juka = int(type_tag.get('PrevJuka').replace(',', ''))
            volume = int(type_tag.get('Volume').replace(',', ''))

        debi = prev_juka-cur_juka
        rate = round(((cur_juka / prev_juka)-1)*100,2)

        return ({'price':cur_juka, 'debi':debi, 'rate':rate, 'volume':volume})

    except HTTPError as e:
        print(e)
        if try_cnt>=3:
            return None
        else:
            get_stock_cur(code,try_cnt=+1)

def get_stock_info(code,try_cnt):
    try:
        temp = requests.get('http://asp1.krx.co.kr/servlet/krx.asp.XMLSiseEng?code=' + code).content
        temp = temp[1:]
        root = ET.fromstring(temp)
        stock_data = []
        DailyStock = []
        for DailyStock1 in root.findall('TBL_DailyStock'):
            for DailyStock2 in DailyStock1.findall('DailyStock'):
                #DailyStock.append(DailyStock2.attrib)
                #date = DailyStock2.get('day_Date')
                date = datetime.datetime.strptime(('20'+ DailyStock2.get('day_Date')).replace("/","-"),'%Y-%m-%d')
                close = int(DailyStock2.get('day_EndPrice').replace(',', ''))
                open = int(DailyStock2.get('day_Start').replace(',', ''))
                high = int(DailyStock2.get('day_High').replace(',', ''))
                low = int(DailyStock2.get('day_Low').replace(',', ''))
                volume = int(DailyStock2.get('day_Volume').replace(',', ''))
                DailyStock.append([date,open,high,low,close,volume])
        DailyStock = list(reversed(DailyStock))

        for TBL_StockInfo in root.findall('TBL_StockInfo'):
            print(TBL_StockInfo.attrib)
            '''
            CurJuka = int(type_tag.get('CurJuka').replace(',', ''))
            PrevJuka = int(type_tag.get('PrevJuka').replace(',', ''))
            Volume = int(type_tag.get('Volume').replace(',', ''))
            StartJuka = int(type_tag.get('StartJuka').replace(',', ''))
            HighJuka = int(type_tag.get('HighJuka').replace(',', ''))
            LowJuka = int(type_tag.get('LowJuka').replace(',', ''))
            High52 = int(type_tag.get('High52').replace(',', ''))
            Low52 = int(type_tag.get('Low52').replace(',', ''))
            UpJuka = int(type_tag.get('UpJuka').replace(',', ''))
            DownJuka = int(type_tag.get('DownJuka').replace(',', ''))
            Per = float(type_tag.get('Per').replace(',', ''))
            Amount = int(type_tag.get('Amount').replace(',', ''))
            FaceJuka = int(type_tag.get('FaceJuka').replace(',', ''))
            '''
        for TBL_Hoga in root.findall('TBL_Hoga'):
            print(TBL_Hoga.attrib)
            '''
            mesuJan0 = int(type_tag.get('mesuJan0').replace(',', ''))
            mesuHoka0 = int(type_tag.get('mesuHoka0').replace(',', ''))
            mesuJan1 = int(type_tag.get('mesuJan1').replace(',', ''))
            mesuHoka1 = int(type_tag.get('mesuHoka1').replace(',', ''))
            mesuJan2 = int(type_tag.get('mesuJan2').replace(',', ''))
            mesuHoka2 = int(type_tag.get('mesuHoka2').replace(',', ''))
            mesuJan3 = int(type_tag.get('mesuJan3').replace(',', ''))
            mesuHoka3 = int(type_tag.get('mesuHoka3').replace(',', ''))
            mesuJan4 = int(type_tag.get('mesuJan4').replace(',', ''))
            mesuHoka4 = int(type_tag.get('mesuHoka4').replace(',', ''))
            medoJan0 = int(type_tag.get('medoJan0').replace(',', ''))
            medoHoka0 = int(type_tag.get('medoHoka0').replace(',', ''))
            medoJan1 = int(type_tag.get('medoJan1').replace(',', ''))
            medoHoka1 = int(type_tag.get('medoHoka1').replace(',', ''))
            medoJan2 = int(type_tag.get('medoJan2').replace(',', ''))
            medoHoka2 = int(type_tag.get('medoHoka2').replace(',', ''))
            medoJan3 = int(type_tag.get('medoJan3').replace(',', ''))
            medoHoka3 = int(type_tag.get('medoHoka3').replace(',', ''))
            medoJan4 = int(type_tag.get('medoJan4').replace(',', ''))
            medoHoka4 = int(type_tag.get('medoHoka4').replace(',', ''))
            '''
        for stockInfo in root.findall('stockInfo'):
            print(stockInfo.attrib)
            '''
            myNowTime = type_tag.get('myNowTime')
            myJangGubun = type_tag.get('myJangGubun')
            kospiJisu = float(type_tag.get('kospiJisu'))
            kospiBuho = int(type_tag.get('kospiBuho'))
            kospiDebi = float(type_tag.get('kospiDebi'))
            kosdaqJisu = float(type_tag.get('kosdaqJisu'))
            kosdaqJisuBuho = int(type_tag.get('kosdaqJisuBuho'))
            kosdaqJisuDebi = float(type_tag.get('kosdaqJisuDebi'))
            '''
        '''
        debi = prev_juka-cur_juka
        rate = round(((cur_juka / prev_juka)-1)*100,2)
        return ({'price':cur_juka, 'debi':debi, 'rate':rate, 'volume':volume})
        '''
        stock_data = [DailyStock,TBL_StockInfo.attrib,TBL_Hoga.attrib,stockInfo.attrib]
        return ({'stock_data':stock_data})
    except HTTPError as e:
        print(e)
        if try_cnt>=3:
            return None
        else:
            get_stock_cur(code,try_cnt=+1)

def get_my_stock():
    ### option 적용 ###
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")

    driver = webdriver.Chrome('chromedriver', options=options)
    ##################

    # 삼성전자, 네이버, SK텔레콤, SK이노베이션, 카카오
    codes = ['005930','035420','017670','096770','035720']

    for code in codes:
        # 네이버 주식페이지 url을 입력합니다.
        url = 'https://m.stock.naver.com/item/main.nhn#/stocks/' + code + '/total'

        # 크롬을 통해 네이버 주식페이지에 접속합니다.
        driver.get(url)

        # 정보를 받아오기까지 2초를 잠시 기다립니다.
        time.sleep(1)

        # 크롬에서 HTML 정보를 가져오고 BeautifulSoup을 통해 검색하기 쉽도록 가공합니다.
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        name = soup.select_one(
            '#header > div.end_header_topinfo > div.flick-container.major_info_wrp > div > div:nth-child(2) > div > div.item_wrp > div > h2').text

        current_price = soup.select_one(
            '#header > div.end_header_topinfo > div.flick-container.major_info_wrp > div > div:nth-child(2) > div > div.stock_wrp > div.price_wrp > strong').text

        rate = soup.select_one('#header > div.end_header_topinfo > div.flick-container.major_info_wrp > div > div:nth-child(2) > div > div.stock_wrp > div.price_wrp > div > span.gap_rate > span.rate').text

        print(name,current_price,rate)

    print('-------')
    # 크롬을 종료합니다.
    driver.quit()
    return myport

def job():
    get_my_stock()

def run():
    schedule.every(15).seconds.do(job) #15초에 한번씩 실행
    while True:
        schedule.run_pending()
'''
if __name__ == "__main__":
    run()
'''

if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)
''''''


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('token')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, SECRET_KEY, algorithms=['HS256'])
            except jwt.InvalidTokenError:
                payload = None

            if payload is None:
                return Response(status=401)

            user_id = payload['id']
            g.user_id = user_id
            g.user = get_user_info(user_id) if user_id else None
        else:
            return Response(status=401)

        return f(*args, **kwargs)

    return decorated_function
