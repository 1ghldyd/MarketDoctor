from bs4 import BeautifulSoup
from selenium import webdriver
import schedule
import time
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pymongo import MongoClient
import jwt      # JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import datetime     # 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
# import hashlib      # 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
import bcrypt
from functools import wraps

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.marketdoctor

SECRET_KEY = '!r1l1a1x2o2g3k3s3'        # JWT 토큰을 만들 때 필요한 비밀문자열입니다.

@app.route('/')
def home():
   return render_template('index.html')

@app.route('/login')
def login():
   return render_template('login.html')

@app.route('/register')
def register():
   return render_template('register.html')


@app.route('/myport')
def myport_update():
   return render_template('myport.html')


# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/api/register', methods=['POST'])
def api_register():
   id = request.form['id']
   pw = request.form['pw']

   pw_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())

   db.user.insert_one({'id':id,'pw':pw_hash,'notice_rate':'','code':[]})

   return jsonify({'result': 'success'})

# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route('/api/login', methods=['POST'])
def api_login():
   id = request.form['id']
   pw = request.form['pw']

   user = db.user.find_one({'id': id},{'_id':False})

   # 찾으면 JWT 토큰을 만들어 발급합니다.
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

      # token을 줍니다.
      return jsonify({'result': 'success','token':token})
   # 찾지 못하면
   else:
      return jsonify({'result': 'fail', 'msg':'아이디/비밀번호가 일치하지 않습니다.'})

# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
@app.route('/api/nick', methods=['GET'])
def api_valid():
   # 토큰을 주고 받을 때는, 주로 header에 저장해서 넘겨주는 경우가 많습니다.
   # header로 넘겨주는 경우, 아래와 같이 받을 수 있습니다.
   token_receive = request.headers['token']

   # try / catch 문?
   # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

   try:
      # token을 시크릿키로 디코딩합니다.
      # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
      payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
      print(payload)

      # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
      # 여기에선 그 예로 닉네임을 보내주겠습니다.
      userinfo = db.user.find_one({'id':payload['id']},{'_id':0})
      return jsonify({'result': 'success','id':userinfo['id']})
   except jwt.ExpiredSignatureError:
      # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
      return jsonify({'result': 'fail', 'msg':'로그인 시간이 만료되었습니다.'})


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


@app.route('/api/myport', methods=['GET'])
def myport():
    token_receive = request.headers['token']
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        port = userinfo['code']
        #port = db.user.find_one({'id': payload['id']}, {'port': {$exists: true}})
        if len(port) != 0:
            #portData = get_my_stock(port)



            return jsonify({'result': 'success', 'code': port})
        else:
            return jsonify({'result': 'fail', 'msg': '등록된 종목이 없습니다.'})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})

@app.route('/api/delete-port', methods=['POST'])
def delete_port():
    # 1. 클라이언트가 전달한 name_give를 name_receive 변수에 넣습니다.
    code = request.form['code']
    # 2. mystar 목록에서 delete_one으로 name이 name_receive와 일치하는 star를 제거합니다.
    db.mystar.delete_one({'code': code})
    # 3. 성공하면 success 메시지를 반환합니다.
    return jsonify({'result': 'success', 'msg': 'delete 연결되었습니다!'})


def get_my_stock(port):
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
    codes = port
    myport = []

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
        myport.append({'code':code,'name':name,'current_price':current_price,'rate':rate })

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