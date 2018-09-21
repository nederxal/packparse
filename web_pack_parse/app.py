#! /usr/bin/python
# -*- coding:utf-8 -*-

import sqlite3
from flask import Flask, request, render_template,g
from datetime import date, datetime

# STUFF ... #
DATABASE = "../songs.db"
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
    return (res[0] if res else None) if one else res
    
app = Flask(__name__)
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

        
        
# VIEWS #
@app.route('/')
def index():
    d = datetime.now()
    d = d.strftime("%d-%m-%Y")
    rows = db_query("SELECT pack_name FROM pack LIMIT 5;")
    return render_template('index.html', date=d, rows=rows)
    

@app.route('/lfp/', methods=['POST'])
def lfp():
    pack_name = request.form["pack_name"]
    rows = db_query('SELECT * FROM pack WHERE pack_name LIKE ? ', [pack_name+'%'])
    return render_template('parse_res.html', pack_name=pack_name, rows=rows)

@app.route('/lfp/<id>')
def lfpid(id):
    pack_name = db_query('SELECT pack_name FROM pack WHERE id = ? ', [id], one=True)
    print (pack_name[0])
    rows = db_query('SELECT song_name, speed, stepper_name, difficulty_block from v_songs where id = ?', [id])
    return render_template('parse_res.html', id=id, pack_name=pack_name[0], rows=rows)

# @app.route('/lfs/')
# def lfs():

if __name__ == '__main__':
    app.run(debug=True)
