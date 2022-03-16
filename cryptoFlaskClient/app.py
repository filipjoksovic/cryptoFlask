import multiprocessing
import random
import threading
import time

from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from flask_socketio import SocketIO
import requests
import eventlet

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = 'filesystem'
Session(app)
socket = SocketIO(app)
api_key = '39802830831bed188884e193d8465226'


url = "http://127.0.0.1:5000/"

clients = {}

cryptoData = {}


def isLoggedIn():
    if "uid" not in session:
        session['uid'] = None
        return False
    if session['uid'] is None:
        return False
    return session['uid']


@app.route('/')
def hello_world():  # put application's code here
    if not isLoggedIn():
        return redirect("/login")
    else:
        return render_template("index.html")


@app.route('/login')
def login():
    return render_template("login.html")


@app.route("/doLogin", methods=["POST"])
def doLogin():
    email = request.form["email"]
    password = request.form["password"]
    data = {
        "email": email,
        "password": password,
        "api_key": api_key
    }
    response = requests.post(url + "login", data).json()
    print(response)
    if response['status'] == 500:
        errors = [response['message']]
        session['errors'] = errors
        return redirect("/login")
    else:
        session['message'] = response['message']
        session['uid'] = response['user']['uid']
        session['email'] = response['user']['email']
        return redirect("/")


@app.route("/logout")
def logout():
    session['uid'] = None
    session['email'] = None
    return redirect("/")


@app.route('/register')
def register():
    return render_template("register.html")


@app.route("/account")
def account():
    print(session['uid'])
    # return 'hello'
    response = requests.get(url + "/account", params={'user_id': session['uid'], 'api_key': api_key}).json()
    account = response['account']
    payment_info = response['payment_info']
    cards = response['cards']
    balance = response['balance']
    return render_template("account.html", account=account, payment_info=payment_info, cards=cards,
                           balance=balance)


@app.route("/editAccount", methods=["POST"])
def editAccount():
    data = {
        "fname": request.form['fname'],
        "lname": request.form["lname"],
        "email": request.form['email'],
        "address": request.form['address'],
        "city": request.form['city'],
        "country": request.form['country'],
        "phone": request.form['phone'],
        "user_id": session['uid'],
        'api_key': api_key
    }
    response = requests.post(url + "/editAccount", data=data).json()
    if response["status"] == 500:
        session['error'] = response['message']
    else:
        session['message'] = response['message']
    return redirect("/account")


@app.route("/addCard", methods=["POST"])
def addCard():
    data = {
        "cholder": request.form["cholder"],
        "cnumber": request.form["cnumber"],
        "valid": request.form["valid"],
        "cvc": request.form["cvc"],
        "user_id": session['uid'],
        'api_key': api_key
    }
    response = requests.post(url + "/addCard", data=data).json()
    if response['status'] == 200:
        session['message'] = response['message']
    else:
        session['error'] = response['message']
    return redirect("/account")


@app.route("/payment")
def payment():
    user_id = session['uid']
    response = requests.get(url + "/payment", params={"user_id": user_id, 'api_key': api_key}).json()
    if response['status'] == 500:
        session['error'] = response['message']
        return redirect("/account")
    else:
        card = response['card']
        balance = response['balance']
        return render_template("payment.html", card=card, balance=balance)


@app.route("/executePayment", methods=["POST"])
def executePayment():
    data = {
        "amount": request.form['ammount'],
        "user_id": session['uid'],
        "api_key": api_key
    }
    response = requests.post(url + "/executePayment", data=data).json()
    if response["status"] == 500:
        response['error'] = response["message"]
    else:
        response['message'] = response["message"]
    return redirect("/account")


@app.route("/transfer")
def transfer():
    response = requests.get(url + "/transfer", params={"user_id": session['uid'], "api_key": api_key}).json()
    if response["status"] == 200:
        balance = response['balance']
        currencies = response["currencies"]
        return render_template("transfer.html", balance=balance, currencies=currencies)
    else:
        session['errors'] = response["message"]
        return redirect("/")


@app.route("/createTransfer", methods=["POST"])
def createTransfer():
    data = {
        "user_id": session['uid'],
        "sender_email": session['email'],
        "email": request.form["email"],
        "value": request.form["quantity"],
        "currency": request.form["currency"],
        "api_key": api_key
    }
    response = requests.post(url + "/createTransfer", data=data).json()
    if response["status"] == 500:
        errors = []
        errors.append(str(response["message"]))
        session['errors'] = errors
        return redirect("/transfer")
    else:
        transaction = response["transaction"]
        print("TDATA")
        print(transaction)
        socket.start_background_task(
            initiateTransaction, transaction["sender_id"], transaction["sender_email"], transaction["receiver_email"],
            transaction["value"], transaction["currency"])
    return response


def initiateTransaction(sender_id, sender_email, email, value, currency):
    data = {
        "sender_id": sender_id,
        "sender_email": sender_email,
        "receiver_email": email,
        "value": value,
        "currency": currency,
        "api_key": api_key
    }
    response = requests.post(url + "/formTransaction", data=data).json()
    if len(response) == 0:
        return redirect("/")
    else:
        transaction = response
        print("Transaction data")
        print(transaction)
        processTransaction(transaction)


def processTransaction(transaction):
    print(transaction)
    data = {
        "currency_id": transaction["currency_id"],
        "id": transaction["id"],
        "sender_id": transaction["sender_id"],
        "value": transaction["value"],
        "receiver_id": transaction["receiver_id"],
        "api_key": api_key
    }
    print("data")
    print(data)
    response = requests.post(url + "/validateTransaction", data=data).json()
    print(response)
    if response['action'] == 'accept':
        # pass
        socket.start_background_task(acceptTransaction, data)
    else:
        socket.start_background_task(rejectTransaction, data)

    try:
        socket.emit("sendTransaction", {"data": "data"}, room=clients[int(data['receiver_id'])])
    except Exception as err:
        print("error occured while notifying the receiver of the transaction. Error text: " + str(err))


def acceptTransaction(data):
    socket.sleep(10)
    response = requests.post(url + "/acceptTransaction", data=data).json()
    print(response)
    try:
        socket.emit("processedTransaction", {"data": "data"}, room=clients[int(data['receiver_id'])])
    except Exception as err:
        print("User not notified because he is not online")


def rejectTransaction(data):
    response = requests.post(url + "/rejectTransaction", data=data).json()
    print(response)
    try:
        socket.emit("processedTransaction", {"data": "data"}, room=clients[int(data['receiver_id'])])
    except Exception as err:
        print("User not notified because he is not online")


@app.route("/transfers")
def transfers():
    response = requests.get(url + "/transfers", params={"user_id": session['uid'], "api_key": api_key}).json()
    if response['status'] == 200:
        sent = response['sent']
        received = response['received']
        return render_template("transfers.html", received=received, sent=sent)
    else:
        return redirect("/")


@app.route("/wallets")
def wallets():
    response = requests.get(url + "/wallets", params={"user_id": session['uid'], "api_key": api_key}).json()
    if response['status'] == 200:
        return render_template("wallets.html", wallets=response['wallets'])
    else:
        print(response['message'])
        return redirect("/")


@app.route("/doRegister", methods=["POST"])
def doRegister():
    data = {
        "fname": request.form['fname'],
        "lname": request.form["lname"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "password": request.form["password"],
        "address": request.form["address"],
        "city": request.form["city"],
        "country": request.form["country"],
        "api_key": api_key
    }
    response = requests.post(url + "/register", data=data).json()
    if response["status"] == 200:
        session['uid'] = response["user"]["uid"]
        session['email'] = response["user"]["email"]
        return redirect("/")
    else:
        response['message'] = response['message']
        return redirect("/register")


@app.route("/getMonetizationDetails")
def getMonetizationDetails():
    user_id = session['uid']
    currency_id = request.args['currency']
    response = requests.get(url + "/getMonetizationDetails",
                            params={"user_id": user_id, "currency": currency_id, "api_key": api_key}).json()
    return response


@app.route("/monetizeCurrency", methods=["POST"])
def monetizeCurrency():
    uid = session['uid']
    cid = request.form['curr_id']
    response = requests.post(url + "/monetizeCurrency",
                             data={"user_id": uid, "curr_id": cid, "amount": request.form["amount"],
                                   "api_key": api_key}).json()
    return response

@socket.on("connect")
def memorizeClient():
    print("client connected")
    clients[session['uid']] = request.sid
    print(clients)


@socket.on('establish_connection')
def rememberUser(user_id):
    print("CONNECTED")
    # print(clients)


@socket.on('disconnect')
def removeUser():
    try:
        clients.pop(session['uid'])
        print("user removed")
    except Exception as err:
        print(str(err))


@socket.on("getCryptoData")
def GetCryptoData(data):
    threadName = "cryptoDataThread" + str(session['uid'])
    threadExists = False
    for thread in threading.enumerate():
        if thread.name == threadName:
            print("Process not started because it is already running")
            threadExists = True
    if not threadExists:
        pr = threading.Thread(target=cryptoDataThread, name=threadName)
        pr.start()
    global cryptoData
    print(cryptoData)
    if len(cryptoData) != 0:
        socket.emit("receiveCryptoData", {"data": cryptoData})


def cryptoDataThread():
    global cryptoData
    print(cryptoData)
    while True:
        cryptoData = requests.get(url + "/getCryptoData").json()
        socket.emit("receiveCryptoData", {"data": cryptoData})
        time.sleep(60)


if __name__ == '__main__':
    socket.run(app, debug=True, host='127.0.0.1', port=5001)
