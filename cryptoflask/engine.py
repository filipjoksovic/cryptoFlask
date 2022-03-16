import json
import sqlite3

import requests


class Engine:
    @staticmethod
    def connect():
        return sqlite3.connect("database.db")

    @staticmethod
    def getUserPaymentInfo(uid):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * from user_cards where owner_id = ?", (uid,))
        card = curr.fetchone()
        return card

    @staticmethod
    def GetUserBalance(uid):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT balance from user_accounts where user_id = ?", (uid,))
        balance = curr.fetchone()
        return balance[0]

    @staticmethod
    def GetCryptoName(currency):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT name from currencies where sname = ? or id = ?", (currency, currency))
        name = curr.fetchone()
        return name[0]

    @staticmethod
    def GetShortCryptoName(currency):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT sname from currencies where name = ? or id = ?", (currency, currency))
        name = curr.fetchone()
        return name[0]

    @staticmethod
    def GetCryptoNameByID(id):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT name from currencies where id = ?", (id,))
        name = curr.fetchone()
        return name[0]

    @staticmethod
    def GetCryptoValue(curr):
        url_usd = 'https://api.coinbase.com/v2/prices/' + curr + '-USD/spot'
        url_eur = 'https://api.coinbase.com/v2/prices/' + curr + '-EUR/spot'
        url_rsd = 'https://api.coinbase.com/v2/prices/' + curr + '-RSD/spot'

        price_usd = ((requests
                      .get(url_usd)).json())
        price_eur = ((requests
                      .get(url_eur)).json())
        price_rsd = ((requests
                      .get(url_rsd)).json())
        name = Engine.GetCryptoName(curr)
        data = {
            "name": name,
            "sname": curr,
            "currency": [price_usd['data']['currency'], price_eur['data']['currency'], price_rsd['data']['currency']],
            "ammount": [price_usd['data']['amount'], price_eur['data']['amount'], price_rsd['data']['amount']]
        }
        return data

    @staticmethod
    def ConvertCryptoToDollars(curr_id):
        cur_sname = Engine.GetShortCryptoName(curr_id)
        data = Engine.GetCryptoValue(cur_sname)
        return float(data['ammount'][0])

    @staticmethod
    def ConvertCryptoToDollarsBySname(curr_id):
        print("CURR ID " + str(curr_id))
        data = Engine.GetCryptoValue(curr_id)
        return float(data['ammount'][0])
    @staticmethod
    def GetAllCryptoData():
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT name,sname from currencies")
        currencies = curr.fetchall()
        print(currencies)
        curdata = []
        for i in range(len(currencies)):
            currency = currencies[i]
            single_data = Engine.GetCryptoValue(currency[1])
            curdata.append(single_data)
        return curdata

    @staticmethod
    def GetCurrencies():
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT id,name,sname from currencies")
        currencies = curr.fetchall()
        return currencies

    @staticmethod
    def GetUserID(email):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT id from users where email = ?", (email,))
        id = curr.fetchone()[0]
        conn.close()
        return id

    @staticmethod
    def GetCurrencyID(currency):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT id from currencies where sname = ? or name = ?", (currency, currency))
        data = curr.fetchone()
        return data[0]

    @staticmethod
    def GetTransactions(user_id):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * FROM transactions where receiver_id = ?", (user_id,))
        return curr.fetchall()

    @staticmethod
    def HandleSpecificTransaction(transaction_id):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT currency_id,receiver_id,value from transactions where hash_id = ? or id = ?", (transaction_id,transaction_id))
        transaction_data = curr.fetchone()
        curr.execute("SELECT * FROM crypto_accounts where user_id = ? and currency_id = ?",
                     (transaction_data[1], transaction_data[0]))
        account = curr.fetchone()
        if account == None:
            curr.execute("INSERT INTO crypto_accounts(user_id,currency_id,balance) VALUES (?,?,?)",
                         (transaction_data[1], transaction_data[0], transaction_data[2]))
            conn.commit()
        else:
            curr.execute("UPDATE crypto_accounts set balance = balance + ?  where user_id = ? and currency_id = ?",
                         (transaction_data[2], transaction_data[1], transaction_data[0]))
            conn.commit()

    @staticmethod
    def GetTransactionByHashID(hash_id):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * FROM transactions where hash_id = ? or id = ?", (hash_id,hash_id))
        tdata = curr.fetchone()
        formatted_transaction = {
            'status': tdata[-2],
            'hash_id': tdata[1],
            'currency': Engine.GetCryptoNameByID(tdata[4]),
            'value': tdata[5],
            'created_at': tdata[-1]
        }
        return formatted_transaction

    @staticmethod
    def GetReceivedTransfers(uid):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * from transactions where receiver_id = ? ORDER BY created_at DESC", (uid,))
        data = curr.fetchall()
        conn.close()
        formatted_data = []
        for row in data:
            formatted_row = {
                'status': row[-2],
                'hash_id': row[1],
                'currency': Engine.GetCryptoNameByID(row[4]),
                'value': row[5],
                'created_at': row[-1]
            }
            formatted_data.append(formatted_row)
        return formatted_data

    @staticmethod
    def GetSentTransfers(uid):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * from transactions where sender_id = ? ORDER BY created_at DESC", (uid,))
        data = curr.fetchall()
        conn.close()
        formatted_data = []
        for row in data:
            formatted_row = {
                'status': row[-2],
                'hash_id': row[1],
                'currency': Engine.GetCryptoNameByID(row[4]),
                'value': row[5],
                'created_at': row[-1]
            }
            formatted_data.append(formatted_row)
        return formatted_data

    @staticmethod
    def GetTransactionByID(id):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * FROM transactions where id = ?", (id,))
        tdata = curr.fetchone()
        formatted_transaction = {
            'status': tdata[-2],
            'hash_id': tdata[1],
            'currency': Engine.GetCryptoNameByID(tdata[4]),
            'value': tdata[5],
            'created_at': tdata[-1]
        }
        return formatted_transaction

    @staticmethod
    def UpdateBalance(uid, newbalance):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("UPDATE user_accounts set balance = ? where user_id = ?", (newbalance, uid))
        conn.commit()

    @staticmethod
    def GetUserWallets(uid):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * FROM crypto_accounts where user_id = ?", (uid,))
        data = curr.fetchall()
        formatted_data = []
        for row in data:
            formatted_row = {
                "cid": row[2],
                "currency": Engine.GetCryptoNameByID(row[2]),
                "balance": row[3]
            }
            formatted_data.append(formatted_row)
        return formatted_data

    @staticmethod
    def GetWalletBalance(uid, curr_id):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT balance from crypto_accounts where user_id = ? AND currency_id = ?", (uid, curr_id))
        balance = curr.fetchone()[0]
        return balance

    @staticmethod
    def TransferFunds(uid, curr_id, amount):
        conn = Engine.connect()
        curr = conn.cursor()
        account = Engine.getUserPaymentInfo(uid)
        if account == None:
            return False
        currency_price = Engine.ConvertCryptoToDollars(curr_id)
        balanceToAdd = amount * currency_price
        print(balanceToAdd)
        curr.execute("UPDATE crypto_accounts set balance = balance - ? where user_id = ? and currency_id = ?",
                     (amount, uid, curr_id))
        conn.commit()
        try:
            curr.execute("UPDATE user_accounts set balance = balance + ? where user_id = ?", (balanceToAdd, uid))
            conn.commit()
        except Exception as err:
            print(str(err))
            return False
        conn.close()
        return True

    @staticmethod
    def UserExists(email):
        conn = Engine.connect()
        curr = conn.cursor()
        curr.execute("SELECT * FROM users where email = ?",(email,))
        user = curr.fetchone()
        if user is None:
            return False
        return True
