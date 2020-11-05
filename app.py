from bs4 import BeautifulSoup

from selenium import webdriver
import schedule
import time

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pymongo import MongoClient
import jwt      # (패키지: PyJWT)
import datetime     # 토큰 만료시간
import bcrypt   # 암호화
from functools import wraps
import requests

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

@app.route('/myport')
def myport_update():
   return render_template('myport.html')


@app.route('/api/register', methods=['POST'])
def api_register():
   id = request.form['id']
   pw = request.form['pw']
   pw_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
   db.user.insert_one({'id':id,'pw':pw_hash,'notice_rate':'','port':[]})
   return jsonify({'result': 'success', 'msg':'회원가입이 완료되었습니다.'})

@app.route('/api/login', methods=['POST'])
def api_login():
   id = request.form['id']
   pw = request.form['pw']
   user = db.user.find_one({'id': id},{'_id':False})

   if bcrypt.checkpw(pw.encode('utf-8'), user['pw']):
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

@app.route('/api/myport', methods=['GET'])
def myport():
    payload = token_payload_read()
    if payload is not None:
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        ports = userinfo['port']
        if len(ports) != 0:
            return jsonify({'result': 'success', 'ports_info': ports})
        else:
            return jsonify({'result': 'success_but', 'msg': '등록된 종목이 없습니다.'})
    else:
        return jsonify({'result': 'fail', 'msg': '다시 로그인 해주세요.'})

@app.route('/api/addport', methods=['POST'])
def add_port():
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

@app.route('/api/deleteport', methods=['POST'])
def delete_port():
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
    current_price = soup.select_one('#lastTick\[6\] > font.f3_r').text
    rate = soup.select_one('#disArr\[0\] > span').text

    return ({'code':code, 'name':name, 'current_price':current_price, 'rate':rate})





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
