#! /usr/bin/python
# -*- coding:utf-8 -*-


from flask import request, render_template,g
from datetime import datetime
from weblistor import app
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs
from weblistor.forms import SearchPack
from sqlalchemy.orm import sessionmaker

# Ajouter le fomrulaire pour la recherche de pack et voir comment intégrer ça dans une requète
# ou un stepper pour trouver quelles songs lui sont associées 

# Faire un 2e formulaire pour la recherche de song et où elles se trouvent (dans quel pack)
# avec toutes les options trouvables dans la table Songs (nom / speed / double / block / difficulty)

@app.route('/', methods=['GET', 'POST'])
def index():
    pack_form = SearchPack(request.form)

    if pack_form.validate_on_submit():
        row = Pack.query.filter(Pack.name.like(pack_form.pack_name.data+"%")).order_by(Pack.name)
        print (type(row))
        return render_template('index.html', row=row, pack_form=pack_form)

    
    row = Pack.query.order_by(Pack.entry_date.desc()).limit(5)
    return render_template('index.html', row=row, pack_form=pack_form)

    

    


