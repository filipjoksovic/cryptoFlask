import json
import random

from flask import Flask
from flask import render_template
from flask import request, jsonify, redirect, session
from flask_cors import CORS, cross_origin

from flask_session import Session
from datetime import datetime
from flask_socketio import SocketIO
import sqlite3
import hashlib
import re
from engine import Engine
import time
import threading
from Crypto.Hash import keccak

app = Flask(__name__)
app.config['SECRET_KEY'] = 'emilijaristic'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
cors = CORS(app)
socket = SocketIO(app)
Session(app)

api_key = hashlib.md5(b'api_key').hexdigest()

clients = {}

print(threading.active_count())


def allowRequest(request):
    try:
        akey = request.form["api_key"]
        if akey == api_key:
            return True
        return {
            "status": 500,
            "message": "Invalid API key"
        }
    except Exception as err:
        try:
            akey = request.args["api_key"]
            if akey == api_key:
                return True
            return {
                "status": 500,
                "message": "Invalid API key"
            }
        except Exception as err:
            return {
                "status": 500,
                "message": "Missing API key"
            }


def getCrypyoData():
    cryptoData = Engine.GetAllCryptoData()
    return cryptoData


@app.route("/getCryptoData")
def getCData():
    response = {
        "status": 200,
        "data": getCrypyoData()
    }
    return response


@app.route('/register', methods=["POST"])
@cross_origin()
def doRegister():
    if allowRequest(request) == True:
        formdata = request.form
        fname = formdata["fname"]
        lname = formdata["lname"]
        email = formdata["email"]
        phone = formdata["phone"]
        password = hashlib.md5(formdata["password"].encode()).hexdigest()
        response = {}
        if Engine.UserExists(email) == False:
            try:
                print(password)
                address = formdata["address"]
                city = formdata["city"]
                country = formdata["country"]
                conn = Engine.connect()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users(fname,lname,address,city,country, email, password, phone) VALUES (?,?,?,?,?,?,?,?)",
                    (fname, lname, address, city, country, email, password, phone))
                conn.commit()
                response = {'status': 200,
                            'message': "Uspesno kreiran nalog.",
                            'user': dict({
                                "uid": cur.lastrowid,
                                "email": email
                            })
                            }
            except Exception as err:
                response['status'] = 500
                response['message'] = "Doslo je do greske. Tekst greske: " + str(err)
                response['user'] = {}
            finally:
                return response
        else:
            response['status'] = 500
            response['message'] = "Korisnik sa datim podacima vec postoji. Izmenite podatke i pokusajte ponovo"
            response['user'] = {}
            return response
    else:
        return allowRequest(request)


@app.route('/login', methods=["POST"])
@cross_origin()
def doLogin():
    if allowRequest(request) == True:
        email = request.form["email"]
        password = hashlib.md5(request.form["password"].encode()).hexdigest()
        conn = Engine.connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        rows = cur.fetchone()
        response = {}
        if rows is None:
            response['status'] = 500
            response['message'] = "Korisnik sa navedenim podacima ne postoji u bazi podataka"
            response['user'] = {}
            return response
        else:
            response['user'] = {
                "uid": rows[0],
                "email": email
            }
            response['status'] = 200
            response["message"] = "Uspesno prijavljivanje. Dobrodosli!"
        return response
    return allowRequest(request)


@app.route("/account")
def account():
    if allowRequest(request) == True:
        response = {}
        try:
            conn = Engine.connect()
            cur = conn.cursor()
            id = request.args["user_id"]
            cur.execute("SELECT * FROM users where id = ?", (id,))
            acc = cur.fetchone()
            print(acc)
            cards = []
            payment_info = []
            cur.execute("SELECT * from user_cards WHERE owner_id = ?", (id,))
            cards = cur.fetchall()
            cur.execute("SELECT * from user_accounts WHERE user_id = ?", (id,))
            payment_info = cur.fetchone()
            balance = None
            if payment_info is None:
                balance = 0
            else:
                balance = payment_info[3]
            print(payment_info)
            response = {
                'status': 200,
                'message': "Podaci o korisniku",
                "account": acc,
                "payment_info": payment_info,
                "cards": cards,
                "balance": balance
            }
        except Exception as err:
            print(str(err))
            response = {
                "status": 500,
                "message": "Greska prilikom obrade zahteva. Tekst greske: " + str(err)
            }
        finally:
            return response
    return allowRequest(request)


@app.route("/editAccount", methods=["POST"])
def editAccount():
    if allowRequest(request):
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        address = request.form['address']
        city = request.form['city']
        country = request.form['country']
        phone = request.form['phone']
        user_id = request.form["user_id"]
        conn = Engine.connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET fname = ?, lname = ?, email = ?, address = ?, city = ?, country = ?, phone = ? WHERE id = ?",
            (fname, lname, email, address, city, country, phone, user_id))
        message = ""
        response = {}
        try:
            conn.commit()
            response = {
                "status": 200,
                "message": "Korisnik je uspesno izmenjen"
            }
        except Exception as err:
            print(str(err))
            response = {
                "status": 200,
                "message": "Doslo je do greske prilikom izmene korisnika"
            }
        finally:
            return response
    return allowRequest(request)


@app.route("/addCard", methods=["POST"])
def addCard():
    if allowRequest(request) == True:
        response = {}
        card_pattern = re.compile(r"^\d{4}[ ]\d{4}[ ]\d{4}[ ]\d{4}$")
        cvc_pattern = re.compile(r"^\d\d\d$")
        valid_pattern = re.compile(r"^\d\d\/\d\d$")
        cholder = request.form["cholder"]
        cnumber = request.form["cnumber"]
        valid = request.form["valid"]
        cvc = request.form["cvc"]
        uid = request.form['user_id']
        errors = []
        if not re.fullmatch(card_pattern, cnumber):
            errors.append("Kartica nije validna")
        if not re.fullmatch(cvc_pattern, cvc):
            errors.append("CVC kod nije validan")
        if not re.fullmatch(valid_pattern, valid):
            errors.append("Datum isteka kartice nije validan")
        else:
            valid = "01/" + valid
            valid_date = datetime.strptime(valid, "%d/%m/%y")
            if datetime.now() > valid_date:
                errors.append("Kartica je istekla")
        if len(errors) > 0:
            session['errors'] = errors
            response = {
                "status": 500,
                "message": errors
            }
            return response
        try:
            conn = Engine.connect()
            curr = conn.cursor()
            curr.execute("insert into user_cards (owner_id,cnumber,cholder,valid,cvc) VALUES(?,?,?,?,?)",
                         (uid, cnumber, cholder, valid, cvc))
            conn.commit()
            try:
                card_id = curr.lastrowid
                curr.execute("insert into user_accounts(user_id,card_id) values(?,?)", (uid, card_id))
                conn.commit()
                response = {
                    "status": 200,
                    "message": "Uspesno izvrsena uplata na nalog"
                }
            except Exception as err:
                print("Error while inserting data into the table. " + str(err))
                errors = []
                errors.append("Greska prilikom verifikacije naloga. Greska: " + str(err))
                # session['errors'] = errors
                response = {
                    "status": 500,
                    "message": errors
                }
        except Exception as err:
            print("Error while inserting data into the table. " + str(err))
            errors = []
            errors.append("Greska prilikom dodavanje sredstva placanja. Greska: " + str(err))
            session['errors'] = errors
        finally:
            conn.close()
            return response
    return allowRequest(request)


@app.route('/getCurrRate', methods=["GET"])
def getCurrencyRate():
    currency = request.args.get('curr')
    curdata = None
    try:
        curdata = Engine.GetCryptoValue(currency)
    except Exception:
        curdata = {}
    return curdata


@app.route("/transfer")
def transfer():
    if allowRequest(request) == True:
        response = {}
        try:
            uid = request.args["user_id"]
            conn = Engine.connect()
            curr = conn.cursor()
            curr.execute("SELECT balance FROM user_accounts WHERE user_id = ?", (uid,))
            balance = curr.fetchone()[0]
            currencies = Engine.GetCurrencies()
            print(currencies)
            response = {
                "status": 200,
                "balance": balance,
                "currencies": currencies
            }
        except Exception as err:
            response = {
                "status": 500,
                "message": str(err)
            }
        finally:
            return response
    return allowRequest(request)


@app.route("/createTransfer", methods=['POST'])
def createTransfer():
    if allowRequest(request) == True:
        print('received request')
        uid = str(request.form["user_id"])
        email = str(request.form['email'])
        sender_email = str(request.form['sender_email'])
        value = str(request.form['value'])
        currency = str(request.form['currency'])
        response = {}
        if not Engine.UserExists(email):
            response = {
                "status": 500,
                "message": "Korisnik sa datom adresom ne postoji"
            }
            return response
        else:
            response = {
                "status": 200,
                "message": "Transakcija zapoceta.",
                "transaction": {
                    "sender_id": uid,
                    "sender_email": sender_email,
                    "receiver_email": email,
                    "value": value,
                    "currency": currency
                }
            }
        return response
    return allowRequest(request)


@app.route("/formTransaction", methods=["POST"])
def formTransaction():
    if allowRequest(request) == True:
        transaction = {}
        print(request.form)
        try:
            sender_id = request.form["sender_id"]
            sender_email = request.form["sender_email"]
            receiver_email = request.form["receiver_email"]
            value = request.form["value"]
            currency = request.form["currency"]
            receiver_id = str(Engine.GetUserID(receiver_email))
            randint = str(random.randint(0, 256))
            hash_id = keccak_hash(sender_email + receiver_email + value + currency + randint)
            currency_id = Engine.GetCurrencyID(currency)
            conn = Engine.connect()
            curr = conn.cursor()
            curr.execute("INSERT into transactions(hash_id,sender_id,receiver_id,currency_id,value) VALUES (?,?,?,?,?)",
                         (hash_id, sender_id, receiver_id, currency_id, value))
            conn.commit()
            transactionID = curr.lastrowid
            transaction = {
                "id": transactionID,
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "currency_id": currency_id,
                "value": value
            }
        except Exception as err:
            transaction = {}
        finally:
            return transaction
    return allowRequest(request)


def initiateTransaction(sender_id, sender_email, email, value, currency):
    receiver_id = str(Engine.GetUserID(email))
    randint = str(random.randint(0, 256))
    hash_id = keccak_hash(sender_email + email + value + currency + randint)
    print("Transaction sent")
    currency_id = Engine.GetCurrencyID(currency)
    conn = Engine.connect()
    curr = conn.cursor()
    curr.execute("INSERT into transactions(hash_id,sender_id,receiver_id,currency_id,value) VALUES (?,?,?,?,?)",
                 (hash_id, sender_id, receiver_id, currency_id, value))
    conn.commit()
    transaction_id = curr.lastrowid
    transaction = Engine.GetTransactionByID(transaction_id)
    # acceptTransaction(hash_id)
    senderbalance = Engine.GetUserBalance(sender_id)
    dollar_value = Engine.ConvertCryptoToDollars(currency_id)
    amountToSend = float(value) * dollar_value
    print(senderbalance)
    print(amountToSend)
    if senderbalance > amountToSend:
        print("HERE HERE HERE")
        print("sender_id" + str(sender_id))
        Engine.UpdateBalance(sender_id, senderbalance - amountToSend)
        threading.Thread(target=acceptTransaction, args=(hash_id, value, currency_id, receiver_id)).start()
    else:
        threading.Thread(target=rejectTransaction, args=(hash_id, value, currency_id, receiver_id)).start()
    socket.emit("sendTransaction",
                {'receiver_id': receiver_id, 'message': transaction}, room=clients[int(receiver_id)])
    return 'Transakcija poslata'


@app.route("/acceptTransaction", methods=["POST"])
def aTrans():
    if allowRequest(request) == True:
        response = {}
        try:
            sender_id = request.form["sender_id"]
            transaction_id = request.form['id']
            value = request.form['value']
            currency_id = request.form['currency_id']
            receiver_id = request.form['receiver_id']
            curprice = Engine.ConvertCryptoToDollars(currency_id)
            newbal = Engine.GetUserBalance(sender_id) - float(curprice) * float(value)
            Engine.UpdateBalance(sender_id, newbal)
            acceptTransaction(transaction_id, value, currency_id, receiver_id)
            response = {
                "status": 200,
                "message": "Uspesno obradjena transakcija"
            }
        except Exception as err:
            response = {
                "status": 500,
                "message": "Greksa prilikom prihvatanja transakcije. Tekst greske: " + str(err)
            }
        finally:
            return response
    return allowRequest(request)


@app.route("/rejectTransaction", methods=["POST"])
def rTrans():
    if allowRequest(request) == True:
        response = {}
        try:
            sender_id = request.form["sender_id"]
            transaction_id = request.form['id']
            value = request.form['value']
            currency_id = request.form['currency_id']
            receiver_id = request.form['receiver_id']
            rejectTransaction(transaction_id, value, currency_id, receiver_id)
            response = {
                "status": 200,
                "message": "Uspesno obradjena transakcija"
            }
        except Exception as err:
            response = {
                "status": 500,
                "message": "Greksa prilikom odbijanja transakcije. Tekst greske: " + str(err)
            }
        finally:
            return response
    return allowRequest(request)


def acceptTransaction(transaction_id, value, currency, receiver_id):
    response = {}
    try:
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("UPDATE transactions set status = 'Odobrena' where id = ?", (transaction_id,))
        conn.commit()
        Engine.HandleSpecificTransaction(transaction_id)
        transaction = Engine.GetTransactionByHashID(transaction_id)
        response = {
            "status": 200,
            "message": "Transakcija uspesno prihvacena."
        }
    except Exception as err:
        response = {
            "status": 500,
            "message": "Doslo je do greske prilikom prihvatanja transakcije. Tekst greske: " + str(err)
        }
    finally:
        return response


def rejectTransaction(transaction_id, value, currency, receiver_id):
    conn = Engine.connect()
    curr = conn.cursor()
    curr.execute("UPDATE transactions set status = 'Odbijena' where id = ?", (transaction_id,))
    conn.commit()
    Engine.HandleSpecificTransaction(transaction_id)
    transaction = Engine.GetTransactionByHashID(transaction_id)
    socket.emit("processedTransaction", {'receiver_id': receiver_id, 'message': transaction})


def keccak_hash(data):
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(str.encode(data))
    return keccak_hash.hexdigest()


@app.route("/validateTransaction", methods=["POST"])
def validateTransaction():
    if allowRequest(request) == True:
        response = {}
        senderbalance = Engine.GetUserBalance(request.form['sender_id'])
        dollar_value = Engine.ConvertCryptoToDollars(request.form["currency_id"])
        amountToSend = float(request.form["value"]) * dollar_value
        if senderbalance > amountToSend:
            response = {
                "action": "accept"
            }
            return response
        else:
            response = {
                "action": "reject"
            }
            return response
    return allowRequest(request)


@app.route("/transfers")
def transfers():
    if allowRequest(request) == True:
        response = {}
        try:
            received_transfers = Engine.GetReceivedTransfers(request.args["user_id"])
            sent_transfers = Engine.GetSentTransfers(request.args["user_id"])
            response = {
                "status": 200,
                "received": received_transfers,
                "sent": sent_transfers
            }
        except Exception as err:
            response = {
                "status": 500,
                "message": str(err)
            }
        finally:
            return response
    return allowRequest(request)


@app.route("/payment")
def payment():
    if allowRequest(request) == True:
        uid = request.args['user_id']
        card = Engine.getUserPaymentInfo(uid)
        response = {}
        if card is None:
            response = {
                "status": 200,
                "message": "Nemate ni jedno dodato sredstvo placanja."
            }
            return response
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * from user_cards WHERE owner_id = ?", (uid,))
        card = curr.fetchone()
        curr.execute("SELECT balance from user_accounts where user_id = ?", (uid,))
        balance = curr.fetchone()
        response = {
            "status": 200,
            "card": card,
            "balance": balance[0]
        }
        return response
    return allowRequest(request)


@app.route('/wallets')
def getUserWallets():
    if allowRequest(request) == True:
        response = {}
        try:
            uid = request.args["user_id"]
            wallets = Engine.GetUserWallets(uid)
            response = {
                "status": 200,
                "wallets": wallets
            }
        except Exception as err:
            response = {
                "status": 500,
                "wallets": {},
                "message": str(err)
            }
        finally:
            return response
    return allowRequest(request)


@app.route("/executePayment", methods=["POST"])
def executePayment():
    if allowRequest(request) == True:
        response = {}
        amount = request.form['amount']
        uid = request.form['user_id']
        conn = Engine.connect()
        curr = conn.cursor()
        try:
            curr.execute("UPDATE user_accounts set balance = balance + ? WHERE user_id = ?", (amount, uid))
            conn.commit()
            response = {
                "status": 200,
                "message": "Uspesno izvrsena uplata na nalog"
            }
        except Exception as err:
            response = {
                "status": 500,
                "message": "Doslo je do greske prilikom izvrsenja uplate. Tekst greske: " + str(err)
            }
        finally:
            conn.close()
            return response
    return allowRequest(request)


@app.route('/getMonetizationDetails')
def getMonetizationData():
    if allowRequest(request) == True:
        user_id = request.args['user_id']
        currency_id = request.args['currency']
        value = Engine.ConvertCryptoToDollars(currency_id)
        response = {
            'message': "Uspesno povuceni podaci",
            'data': {
                'user_balance': Engine.GetWalletBalance(user_id, currency_id),
                'currency': Engine.GetCryptoName(currency_id),
                'currency_sname': Engine.GetShortCryptoName(currency_id),
                'currency_value': value
            }
        }
        return response
    return allowRequest(request)


@app.route("/monetizeCurrency", methods=["POST"])
def monetizeCurrency():
    if allowRequest(request) == True:
        uid = request.form["user_id"]
        cid = request.form['curr_id']
        amount = float(request.form['amount'])
        if Engine.TransferFunds(uid, cid, amount) == True:
            response = {
                'message': "Uspesno izvrsena zamena novca"
            }
            return response
        else:
            response = {
                'message': 'Doslo je do greske prilikom zamene novca. Za unovcavanje valute morate imati podeseno sredstvo placanja'
            }
            return response
    return allowRequest(request)


cryptoData = []

if __name__ == '__main__':
    # app.run()
    # getData()

    socket.run(app, debug=True,host='127.0.0.1', port=5000)
