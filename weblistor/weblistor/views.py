#! /usr/bin/python
# -*- coding:utf-8 -*-


from flask import request, render_template, redirect, url_for, session, flash
from datetime import datetime
from sqlalchemy.orm import sessionmaker, session
from werkzeug.datastructures import ImmutableMultiDict
from weblistor import app
from weblistor.tables import Pack, Songs
from weblistor.forms import SearchPack, SearchSong, flash_errors


@app.route('/', methods=['GET', 'POST'])
def index():
    pack_form = SearchPack(request.form)
    song_form = SearchSong(request.form)

    if pack_form.validate_on_submit():
        pack_name = request.form.get('pack_name')
        row = Pack.query.filter(Pack.name.like("%"+pack_name+"%")) \
                        .order_by(Pack.name).all()

        return render_template('index.html', row=row, pack_name=pack_name,
                               pack_form=pack_form, song_form=song_form)

    if pack_form.errors:
        flash_errors(pack_form)

    row = Pack.query.order_by(Pack.entry_date.desc()).limit(5)

    return render_template('index.html', row=row,
                           pack_form=pack_form, song_form=song_form)


# Résultat si id du pack pour voir le contenu
@app.route('/pid/<int:id>', methods=['GET'])
def list_pack(id):
    song_row, data_row = Songs.get_songs_pack(id)

    return render_template('pack.html', song_row=song_row, data_row=data_row)


@app.route('/sli', methods=['GET', 'POST'])
def songs_search():
    sql_params = request.form.to_dict()

    # Dirty fixes
    if "double" not in sql_params:
        sql_params["double"] = False
    else:
        sql_params["double"] = True

    if len(sql_params["speed_low"]) == 0:
        sql_params["speed_low"] = 0

    if len(sql_params["speed_high"]) == 0:
        sql_params["speed_high"] = 1000

    try:
        # Still dirty checks (you're allowed to puke)
        int(sql_params["speed_low"])
        int(sql_params["speed_high"])

    except ValueError as e:
        flash("Wow gamin la vitesse avec des nombres pas des lettres !")
        return redirect(url_for('index'))

    song_list = Songs.search_song(sql_params["song_name"],
                                  sql_params["speed_low"],
                                  sql_params["speed_high"],
                                  sql_params["block"],
                                  sql_params["double"],
                                  sql_params["stepper"])

    if not song_list:
        flash("Déso pas déso rien ne correspond à ta recherche")
        return redirect(url_for('index'))

    return render_template('songs.html', song_list=song_list)
