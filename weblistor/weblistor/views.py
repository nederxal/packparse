#! /usr/bin/python
# -*- coding:utf-8 -*-


from flask import request, render_template, redirect, url_for, session, g
from datetime import datetime
from weblistor import app  # , db
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs
from weblistor.forms import SearchPack
from sqlalchemy.orm import sessionmaker, session

# Ajouter le fomrulaire pour la recherche de pack et voir comment intégrer ça
# dans une requète ou un stepper pour trouver quelles songs lui sont associées

# Faire un 2e formulaire pour la recherche de song et où elles se trouvent
# avec toutes les options trouvables dans la table Songs
# (nom / speed / double / block / difficulty)


@app.route('/', methods=['GET', 'POST'])
def index():
    pack_form = SearchPack(request.form)

    if pack_form.validate_on_submit():
        return redirect(url_for('search_pack', name=pack_form.pack_name.data))

    row = Pack.query.order_by(Pack.entry_date.desc()).limit(5)
    return render_template('index.html', row=row, pack_form=pack_form)


# Résultat recherche avec nom du pack
@app.route('/pack/<name>', methods=['GET', 'POST'])
def search_pack(name):
    pack_form = SearchPack(request.form)

    if pack_form.validate_on_submit():
        return redirect(url_for('search_pack', name=pack_form.pack_name.data))

    row = Pack.query.filter(Pack.name.like(name+"%")).order_by(Pack.name)

    return render_template('pack.html', row=row, pack_form=pack_form)


# Résultat si id du pack pour voir le contenu
@app.route('/pack/id/<id>', methods=['GET', 'POST'])
def list_pack(id):
    pack_form = SearchPack(request.form)

    if pack_form.validate_on_submit():
        return redirect(url_for('search_pack', name=pack_form.pack_name.data))

    # Soucis avec les noms des colonnes dans les tables ... on se retoruve avec
    # 2 fois "name" le dernier écrasant tout et on se retrouve avec le chemin
    # de la banner ... on traîte comme un tableau -> OK
    song_row = Songs.get_songs_pack(id)
    data_row = Songs.get_songs_data(id)

    return render_template('songs.html', pack_form=pack_form,
                           song_row=song_row, data_row=data_row)
