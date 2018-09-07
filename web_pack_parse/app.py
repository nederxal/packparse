#! /usr/bin/python
# -*- coding:utf-8 -*-

import sqlite3
from flask import Flask, request, render_template,g
from datetime import date, datetime

DATABASE = r"C:\Users\adelanchy.AYXO\Documents\GitHub\packparse\songs.db"
def db_conn():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db
    
def db_query(query, args=(), one=False):
    cur = db_conn().execute(query, args)
    res = cur.fetchall()
    cur.close
    return res
    
app = Flask(__name__)
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        
@app.route('/')
def index():
    d = datetime.now()
    d = d.strftime("%d-%m-%Y")
    rows = db_query("SELECT pack_name FROM pack;")
    return render_template('index.html', date=d, rows=rows)
    
    
# @app.route('/pack/')
# @app.route('/pack/<pack_name>')
#def pack_
# @app.route("/contact/", methods=['GET', 'POST'])
# def contact():
    # if request.method == 'GET':
        # mail = "jean@bonno.fr"
        # tel = "tel"
        # return "Mail : {} --- Tel : {}".format(mail, tel)
    # else:
        # return "C'est la poste mec !"

# @app.route("/coucou/")
# def dir_coucou():
    # return "coucou"

# @app.route("/la/")
# def ici():
    # return "Le chemin est : " + request.path
    
if __name__ == '__main__':
    app.run(debug=True)
