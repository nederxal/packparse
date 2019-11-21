#! /usr/bin/python
# -*- coding:utf-8 -*-


from flask import request, render_template, redirect, url_for, session, g
from datetime import datetime
from sqlalchemy.orm import sessionmaker, session
from weblistor import app
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs
from weblistor.forms import SearchPack, SearchSong

# Faire un 2e formulaire pour la recherche de song et où elles se trouvent
# avec toutes les options trouvables dans la table Songs
# (nom / stepper / speed / double / block / difficulty)


@app.route('/', methods=['GET', 'POST'])
def index():
    pack_form = SearchPack(request.form)
    song_form = SearchSong(request.form)

    if pack_form.validate_on_submit():
        pack_name = request.form.get('pack_name')
        row = Pack.query.filter(Pack.name.like("%"+pack_name+"%")) \
                        .order_by(Pack.name)
    else:
        row = Pack.query.order_by(Pack.entry_date.desc()).limit(5)

    return render_template('index.html', row=row,
                           pack_form=pack_form, song_form=song_form)


# Résultat si id du pack pour voir le contenu
@app.route('/pid/<id>', methods=['GET', 'POST'])
def list_pack(id):
    # Soucis avec les noms des colonnes dans les tables ... on se retoruve avec
    # 2 fois "name" le dernier écrasant tout et on se retrouve avec le chemin
    # de la banner ... on traîte comme un tableau -> OK
    song_row, data_row = Songs.get_songs_pack(id)

    return render_template('pack.html', song_row=song_row, data_row=data_row)


@app.route('/sli', methods=['POST'])
def songs_search():
    print(request.form)
    return ("Hello world")
