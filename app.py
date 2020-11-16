from bs4 import BeautifulSoup
import requests

#from selenium import webdriver
import schedule
import time
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
import jwt      # (패키지: PyJWT)
from datetime import datetime, timedelta     # 토큰 만료시간
import bcrypt   # 암호화

from urllib.request import HTTPError
import xml.etree.ElementTree as ET

from bokeh.plotting import figure
from bokeh.layouts import gridplot
from bokeh.models import NumeralTickFormatter,HoverTool,ColumnDataSource
from bokeh.embed import json_item
import json
import pandas as pd

from threading import Thread, Lock, Semaphore

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.marketdoctor

SECRET_KEY = '!r1l1a1x2o2g3k3s3'        # JWT 토큰을 만들 때 필요한 비밀문자열입니다.

get_stock_cur_data = []     # 멀티스레드용 전역함수
get_stock_cur_data_lock = Lock()
pool_sema = Semaphore(8)

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
         'exp': datetime.utcnow() + timedelta(seconds=60*60*24)   #24시간 유효
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
        if (request.form['notice_rate_up'] == ""):
            notice_rate_up = ""
        else:
            notice_rate_up = float(request.form['notice_rate_up'].replace('%', ''))
        if (request.form['notice_rate_down'] == ""):
            notice_rate_down = ""
        else:
            notice_rate_down = float(request.form['notice_rate_down'].replace('%', ''))
        db.user.update_one({'id': user_data['id']}, {'$set': {'email': request.form['email'], 'notice_rate_up': notice_rate_up, 'notice_rate_down': notice_rate_down}})
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
            '''
            ports = []
            for port in ports_data:
                port_info = get_stock_cur(port['code'],1)
                ports.append({'code':port['code'], 'name':port['name'], 'current_price':port_info['price'], 'debi':port_info['debi'], 'rate':port_info['rate'], 'volume':port_info['volume']})
            return jsonify({'result': 'success', 'ports_data': ports})
            '''

            with get_stock_cur_data_lock:
                global get_stock_cur_data
                get_stock_cur_data = []

            start_time = time.time()
            ts = [Thread(target=get_stock_cur, args=(port_data,1), daemon=True)
                  for port_data in ports_data]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            duration = time.time() - start_time
            print(f"Downloaded current stock data {len(ports_data)} in {duration} seconds")
            return jsonify({'result': 'success', 'ports_data': get_stock_cur_data})
        else:
            return jsonify({'result': 'success_but', 'msg': '등록된 종목이 없습니다.'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/myport-info', methods=['POST'])
def myport_info():
    payload = token_payload_read()
    if payload is not None:
        start_time = time.time()
        stock_data = get_stock_info(request.form['code'], 1)
        duration = time.time() - start_time
        print(f"Downloaded seleted current stock info in {duration} seconds")
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
    p_candlechart = figure(sizing_mode='scale_width', plot_height=150, x_range=(-1, len(df)), tools=['crosshair'])

    inc = df.close >= df.open
    dec = df.open > df.close
    inc_source = ColumnDataSource(data=dict(
        x1=df.index[inc],
        top1=df.open[inc],
        bottom1=df.close[inc],
        high1=df.high[inc],
        low1=df.low[inc],
        volume1=df.volume[inc]
    ))
    dec_source = ColumnDataSource(data=dict(
        x2=df.index[dec],
        top2=df.open[dec],
        bottom2=df.close[dec],
        high2=df.high[dec],
        low2=df.low[dec],
        volume2=df.volume[dec]
    ))
    width = 0.8
    p_candlechart.segment(x0='x1', y0='high1', x1='x1', y1='low1', source=inc_source, color="red")
    p_candlechart.segment(x0='x2', y0='high2', x1='x2', y1='low2', source=dec_source, color="blue")
    r1 = p_candlechart.vbar(x='x1', width=width, top='top1', bottom='bottom1', source=inc_source, fill_color="red", line_color="red")
    r2 = p_candlechart.vbar(x='x2', width=width, top='top2', bottom='bottom2', source=dec_source, fill_color="blue", line_color="blue")
    p_candlechart.yaxis[0].formatter = NumeralTickFormatter(format='0,0')
    p_candlechart.xaxis.ticker = [0,1,2,3,4,5,6,7,8,9]
    p_candlechart.xaxis.visible = False
    p_candlechart.add_tools(HoverTool(
        renderers=[r1],
        tooltips=[
            ("Open", "@top1"),
            ("High", "@high1"),
            ("Low", "@low1"),
            ("Close", "@bottom1")
        ]))
    p_candlechart.add_tools(HoverTool(
        renderers=[r2],
        tooltips=[
            ("Open", "@top2"),
            ("High", "@high2"),
            ("Low", "@low2"),
            ("Close", "@bottom2")
        ]))

    p_volumechart = figure(sizing_mode='scale_width', plot_height=100, x_range=p_candlechart.x_range, tools=['crosshair'])
    r3 = p_volumechart.vbar(x='x1', width=width, top='volume1', source=inc_source, fill_color="black", line_color="black")
    r4 = p_volumechart.vbar(x='x2', width=width, top='volume2', source=dec_source, fill_color="black", line_color="black")
    p_volumechart.yaxis[0].formatter = NumeralTickFormatter(format='0,0')
    p_volumechart.xaxis.ticker = [0,1,2,3,4,5,6,7,8,9]
    p_volumechart.add_tools(HoverTool(renderers=[r3], tooltips=[("volume", "@volume1")]))
    p_volumechart.add_tools(HoverTool(renderers=[r4], tooltips=[("volume", "@volume2")]))

    p_volumechart.xaxis.major_label_overrides = {
        i: date.strftime('%m/%d') for i, date in enumerate(pd.to_datetime(df["date"]))
    }

    p = gridplot([[p_candlechart], [p_volumechart]], toolbar_location=None)

    jsonified_p = json_item(model=p, target="myplot")
    return json.dumps(jsonified_p, ensure_ascii=False, indent='\t')

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
            yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            user_data['port'].append({'code': add_code, 'name': port_info['name'],'notice_date':yesterday})
            db.user.update_one({'id': user['id']}, {'$set': {'port': user_data['port']}})

            if db.port.find_one({'code': add_code}, {'_id': 0}) is None:
                db.port.insert_one({'code': add_code, 'name': port_info['name']})

            return jsonify({'result': 'success', 'msg': '종목이 추가되었습니다!'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/myport-modify-del', methods=['POST'])
def myport_del():
    user = token_payload_read()
    if user is not None:
        user_data = db.user.find_one({'id': user['id']},{'_id':False})
        delete_code = request.form['code']
        delete_name = request.form['name']

        for index, sList in enumerate(user_data['port']):
            if sList['code'] == delete_code and sList['name'] == delete_name :
                del_index = index
        del user_data['port'][del_index]
        db.user.update_one({'id': user['id']}, {'$set': {'port': user_data['port']}})

        if db.user.find_one({'port.code': delete_code}, {'_id': 0}) is None:
            db.port.delete_one({'code': delete_code})

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

    #return ({'code':code, 'name':name, 'current_price':current_price, 'rate':rate})
    return ({'code':code, 'name':name})


def get_stock_cur(port_data,try_cnt):
    with pool_sema:
        try:
            temp = requests.get('http://asp1.krx.co.kr/servlet/krx.asp.XMLSiseEng?code=' + port_data['code']).content
            if len(temp) != 0:
                temp = temp[1:]
                root = ET.fromstring(temp)
                for type_tag in root.findall('TBL_StockInfo'):
                    if type_tag.get('CurJuka') == "":
                        return None
                    cur_juka = int(type_tag.get('CurJuka').replace(',', ''))
                    prev_juka = int(type_tag.get('PrevJuka').replace(',', ''))
                    volume = int(type_tag.get('Volume').replace(',', ''))
                    DungRak = type_tag.get('DungRak')

                debi = cur_juka-prev_juka # 사실 javascript에서 구현해도 됨. (index.js : 308, debiPerc)
                rate = round(((cur_juka / prev_juka)-1)*100,2)

                for stockInfo in root.findall('stockInfo'):
                    myJangGubun = stockInfo.get('myJangGubun')
                    myNowTime = stockInfo.get('myNowTime')

                with get_stock_cur_data_lock:
                    global get_stock_cur_data
                    get_stock_cur_data.append({'code':port_data['code'], 'name':port_data['name'], 'current_price':cur_juka, 'debi':debi, 'rate':rate, 'volume':volume, 'myJangGubun':myJangGubun, 'myNowTime':myNowTime, 'DungRak':DungRak})

        except HTTPError as e:
            print(e)
            if try_cnt>=3:
                print('강제종료-네트워크 지연')
                return None
            else:
                get_stock_cur(code,try_cnt=+1)

def get_stock_info(code,try_cnt):
    try:
        temp = requests.get('http://asp1.krx.co.kr/servlet/krx.asp.XMLSiseEng?code=' + code).content
        temp = temp[1:]
        root = ET.fromstring(temp)
        DailyStock = []
        for DailyStock1 in root.findall('TBL_DailyStock'):
            for DailyStock2 in DailyStock1.findall('DailyStock'):
                #DailyStock.append(DailyStock2.attrib)
                #date = DailyStock2.get('day_Date')
                date = datetime.strptime(('20'+ DailyStock2.get('day_Date')).replace("/","-"),'%Y-%m-%d')
                close = int(DailyStock2.get('day_EndPrice').replace(',', ''))
                open = int(DailyStock2.get('day_Start').replace(',', ''))
                high = int(DailyStock2.get('day_High').replace(',', ''))
                low = int(DailyStock2.get('day_Low').replace(',', ''))
                volume = int(DailyStock2.get('day_Volume').replace(',', ''))
                DailyStock.append([date,open,high,low,close,volume])
        DailyStock = list(reversed(DailyStock))

        for TBL_StockInfo in root.findall('TBL_StockInfo'):
            print('XML.TBL_StockInfo.attrib: ', TBL_StockInfo.attrib) # {'JongName', 'CurJuka', 'DungRak', 'Debi', 'PrevJuka', 'Volume', 'Money', 'StartJuka', 'HighJuka', 'LowJuka', 'High52', 'Low52', 'UpJuka', 'DownJuka', 'Per', 'Amount', 'FaceJuka'}
        '''
        for TBL_Hoga in root.findall('TBL_Hoga'):
            print(TBL_Hoga.attrib) # {'mesuJan0', 'mesuHoka0', 'mesuJan1', 'mesuHoka1', 'mesuJan2', 'mesuHoka2', 'mesuJan3', 'mesuHoka3', 'mesuJan4', 'mesuHoka4', 'medoJan0', 'medoHoka0', 'medoJan1', 'medoHoka1', 'medoJan2', 'medoHoka2', 'medoJan3', 'medoHoka3', 'medoJan4', 'medoHoka4'}
        '''
        for stockInfo in root.findall('stockInfo'):
            print('XML.stockInfo.attrib: ', stockInfo.attrib) # {'kosdaqJisu', 'kosdaqJisuBuho', 'kosdaqJisuDebi', 'starJisu', 'starJisuBuho', 'starJisuDebi', 'jisu50', 'jisu50Buho', 'jisu50Debi', 'myNowTime', 'myJangGubun', 'myPublicPrice', 'krx100Jisu', 'krx100buho', 'krx100Debi', 'kospiJisu', 'kospiBuho', 'kospiDebi', 'kospi200Jisu', 'kospi200Buho', 'kospi200Debi'}
        '''
        debi = prev_juka-cur_juka
        rate = round(((cur_juka / prev_juka)-1)*100,2)
        return ({'price':cur_juka, 'debi':debi, 'rate':rate, 'volume':volume})
        '''
        stock_data = [DailyStock,TBL_StockInfo.attrib,stockInfo.attrib] #TBL_Hoga.attrib,
        return ({'stock_data':stock_data})
    except HTTPError as e:
        print(e)
        if try_cnt>=3:
            return None
        else:
            get_stock_info(code,try_cnt=+1)

def get_my_stock():
    if db.port.find() is not None:
        ports_data = list(db.port.find())
        codes = []
        for port_data in ports_data:
            codes.append({'code': port_data['code'], 'name':port_data['name']})
        with get_stock_cur_data_lock:
            global get_stock_cur_data
            get_stock_cur_data = []

        start_time = time.time()
        ts = [Thread(target=get_stock_cur, args=(code, 1), daemon=True)
              for code in codes]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        duration = time.time() - start_time
        print(f"Downloaded current stock data {len(ports_data)} in {duration} seconds")

        print(get_stock_cur_data)
        if(len(get_stock_cur_data) != 0):
            if(get_stock_cur_data[0]['myJangGubun'] == 'OnMarket'):
                with get_stock_cur_data_lock:
                    stock_datas = get_stock_cur_data[:]
                target_lists = []
                for stock_data in stock_datas:
                    yesterday = (datetime.now() - timedelta(days=1)).replace(hour=15, minute=21, second=0, microsecond=0)
                    if float(stock_data['rate']) > 0:
                        targets = list(db.user.find({'port.code': stock_data['code'], 'port.notice_date': {'$lte': yesterday}, 'notice_rate_up': {'$lte': float(stock_data['rate'])}},{'_id': False, 'pw': False, 'port': False}))
                        for target in targets:
                            target_lists.append({'email': target['email'], 'code': stock_data['code'], 'name': stock_data['name'], 'notice_rate_direction':'up', 'notice_rate': target['notice_rate_up'], 'id':target['id'], 'current_price': stock_data['current_price'], 'debi': stock_data['debi'], 'rate': stock_data['rate'],'myNowTime': stock_data['myNowTime']})
                    elif float(stock_data['rate']) < 0:
                        targets = list(db.user.find({'port.code': stock_data['code'], 'port.notice_date': {'$lte': yesterday}, 'notice_rate_down': {'$gte': float(stock_data['rate'])}},{'_id': False, 'pw': False, 'port': False}))
                        for target in targets:
                            target_lists.append({'email': target['email'], 'code': stock_data['code'], 'name': stock_data['name'], 'notice_rate_direction':'down', 'notice_rate': target['notice_rate_down'], 'id':target['id'], 'current_price': stock_data['current_price'], 'debi': stock_data['debi'], 'rate': stock_data['rate'],'myNowTime': stock_data['myNowTime']})

                target_lists_sort = []
                for target_list in target_lists:
                    target_lists_sort.append(target_list['id'])
                target_lists_sort = list(set(target_lists_sort))
                email_data = target_lists_sort[:]
                i = 0
                for id in target_lists_sort:
                    email_data_stock_info = []
                    for target_list in target_lists:
                        if target_list['id'] == id:
                            email_data_stock_info.append({'name':target_list['name'],'code':target_list['code'],'notice_rate_direction':target_list['notice_rate_direction'],'notice_rate':target_list['notice_rate'], 'current_price': stock_data['current_price'], 'debi': stock_data['debi'], 'rate': stock_data['rate']})
                            email = target_list['email']
                    email_data[i] = {'id':id,'email':email,'myNowTime': stock_data['myNowTime'],'stock_info':email_data_stock_info}
                    i += 1
                print(email_data)

                start_time = time.time()
                ts = [Thread(target=send_mail, args=(data,), daemon=True)
                      for data in email_data]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                duration = time.time() - start_time
                print(f"Sended email in {duration} seconds")
            else:
                print(get_stock_cur_data[0]['myJangGubun'])
        else:
            print('len(get_stock_cur_data) : 0')

def send_mail(data):
    # 내 이메일 정보를 입력합니다.
    me = "marketdoctor.notice@gmail.com"
    # 내 비밀번호를 입력합니다.
    my_password = "sgligoluramjhrrr"

    #for data in email_data:
    # 이메일 받을 상대방의 주소를 입력합니다.
    you = data['email']

    with get_stock_cur_data_lock:
        user_data = db.user.find_one({'id': data['id']}, {'_id': 0})
    ports_data = user_data['port']
    today = datetime.now()

    sub_name = []
    html_content = []
    for for_data in data['stock_info']:
        ret = int(next((index for (index, item) in enumerate(ports_data) if item['code'] == for_data['code']), None))
        ports_data[ret]['notice_date'] = today
        with get_stock_cur_data_lock:
            db.user.update_one({'id': data['id']}, {'$set': {'port': ports_data}})
        sub_name.append(for_data['name'] + " ")
        html_content.append(for_data['name'] + "(" + for_data['code'] + ") 전일대비 " + str(for_data['notice_rate']) + "% 이상 " + for_data['notice_rate_direction'] + " - 현재가 : " + str(for_data['current_price']) + "(" + str(for_data['debi']) + " / " + str(for_data['rate']) + ")" + "<br/>")
    sub_name = ''.join(sub_name)
    html_content = ''.join(html_content)

    ## 여기서부터 코드를 작성하세요.
    # 이메일 작성 form을 받아옵니다.
    msg = MIMEMultipart('alternative')
    # 제목을 입력합니다.
    msg['Subject'] = "MarketDoctor 알림 : " + sub_name
    # 송신자를 입력합니다.
    msg['From'] = me
    # 수신자를 입력합니다.
    msg['To'] = you
    # 이메일 내용을 작성합니다.
    html = 'MarketDoctor가 안내드립니다.<br/>알림 설정하신 종목을 확인하세요!<br/>* ' + data['myNowTime'] + ' 기준<br/><br/>' + html_content

    # 이메일 내용의 타입을 지정합니다.
    part2 = MIMEText(html, 'html')
    # 이메일 form에 작성 내용을 입력합니다
    msg.attach(part2)
    ## 여기에서 코드 작성이 끝납니다.

    # Gmail을 통해 전달할 것임을 표시합니다.
    s = smtplib.SMTP_SSL('smtp.gmail.com')
    # 계정 정보를 이용해 로그인합니다.
    s.login(me, my_password)
    # 이메일을 발송합니다.
    s.sendmail(me, you, msg.as_string())
    # 이메일 보내기 프로그램을 종료합니다.
    s.quit()

    print(data['id'], '고객에게 메일 발송 완료')

def run():
    Thread(target=job_scheduled, daemon=True).start()

def job_scheduled():
    schedule.every(10).seconds.do(job) #10초에 한번씩 실행

    now = datetime.now()
    time = now.replace(hour=15, minute=20, second=0, microsecond=0)
    while now < time:
        schedule.run_pending()
        sleep(1)
        now = datetime.now()

def job():
    get_my_stock()

'''
if __name__ == "__main__":
    sched = BackgroundScheduler(daemon=True)
    sched.start()
    sched.add_job(run, 'cron', hour='9', minute='0', id="check_stock_send_email")
    app.run('0.0.0.0',port=5000,debug=True)

def find():
    finded = list(db.user.find({'port.code':'035420', 'notice_rate_down':{'$lte':-5}}, {'_id': False, 'id':False, 'pw':False,'port':False}))
    print(finded)

def send():
    today = datetime.datetime.now()
    user_data = db.user.find_one({'id': 'test1@naver.com'}, {'_id': 0})
    ports_data = user_data['port']
    ret = int(next((index for (index, item) in enumerate(ports_data) if item['code'] == '207940'), None))
    ports_data[ret]['notice_date'] = today
    db.user.update_one({'id': 'test1@naver.com'}, {'$set': {'port': ports_data}})

def time_calc():
    #yesterday = datetime.now() - timedelta(days=1)
    #print(yesterday)
    #yesterday = (datetime.now() - timedelta(days=1)).replace(hour=15, minute=21, second=0, microsecond=0)
    now = datetime.now()
    time = now.replace(hour=21, minute=30, second=0, microsecond=0)
    print(now < time)

'''
if __name__ == '__main__':
   #find()
   #send()
   #time_calc()
   #job_scheduled()
   #get_my_stock()
   #run()
   app.run('0.0.0.0',port=5000,debug=True)