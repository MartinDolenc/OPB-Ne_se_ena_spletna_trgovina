#!/usr/bin/python
# -*- encoding: utf-8 -*-

# uvozimo bottle.py
from bottle import *

# uvozimo ustrezne podatke za povezavo
import auth_public as auth

#uvozimo paket, za datume
import datetime

# uvozimo psycopg2
import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)  # se znebimo problemov s šumniki

import hashlib  # računanje MD5 kriptografski hash za gesla

import json     # za shranjevanje košare

# odkomentiraj, če želiš sporočila o napakah
debug(True)

secret = "to skrivnost je zelo tezko uganiti 1094107c907cw982982c42"
adminGeslo = "1234"

######################################################################
# seznami in slovarji za pomoč

kategorije = ["Filmi", "Glasba", "Igre", "Knjige", "TV serije"]

slovar_kategorij = {"Filmi": "Film", "Glasba": "Glasba", "Igre": "Igra", "Knjige": "Knjiga", "TV serije": "TV serija"}

######################################################################
# Pomožne funkcije

def password_md5(s):
    """Vrni MD5 hash danega UTF-8 niza. Gesla vedno spravimo v bazo
       kodirana s to funkcijo."""
    h = hashlib.md5()
    h.update(s.encode('utf-8'))
    return h.hexdigest()

def get_user():
    """Poglej cookie in ugotovi, kdo je prijavljeni uporabnik,
       vrni njegov username in ime. Če ni prijavljen, presumeri
       na stran za prijavo ali vrni None (advisno od auto_login).
    """
    # Dobimo username iz piškotka
    username = request.get_cookie('username', secret=secret)
    # Preverimo, ali ta uporabnik obstaja
    if username is not None:
        cur.execute("SELECT username FROM uporabnik WHERE username=%s", [username])
        r = cur.fetchone()
        if r is not None:
            # uporabnik obstaja, vrnemo njegove podatke
            return username
    # Če pridemo do sem, uporabnik ni prijavljen, naredimo redirect
    else:
        return None

def is_admin(username):
    if username is not None:
        cur.execute("SELECT isadmin FROM uporabnik WHERE username=%s", [username])
        return cur.fetchone()[0]
    else:
        return False

def postani_admin():
    username = get_user()
    adminPassword = request.forms.adminPassword
    password = request.forms.password
    cur.execute("SELECT * FROM izdelek ORDER BY ocena DESC")
    izdelki = cur.fetchall()
    cur.execute("SELECT id, ime FROM izdelek ORDER BY RANDOM() LIMIT 1")
    randIzdelek = cur.fetchone()

    if password == "":
        if adminPassword == adminGeslo:
            cur.execute("UPDATE uporabnik SET isadmin = True WHERE username=%s", [username])
            admin = is_admin(username)
            return template('zacetna_stran.html', kategorije=kategorije, napakaO=None, username=username, admin=admin, izdelki=izdelki, idRandIzdelek=randIzdelek[0], imeRandIzdelek=randIzdelek[1])
        else:
            admin = is_admin(username)
            return template('zacetna_stran.html', kategorije=kategorije, napakaO="Vnesili ste napačno admin geslo.", username=username,
                            admin=admin, izdelki=izdelki, idRandIzdelek=randIzdelek[0], imeRandIzdelek=randIzdelek[1])
    else:
        cur.execute("SELECT password FROM uporabnik WHERE username=%s", [username])
        if cur.fetchone()[0] == password_md5(password):
            cur.execute("DELETE FROM uporabnik WHERE username=%s", [username])
            response.delete_cookie('username')
            return template('zacetna_stran.html', kategorije=kategorije, napakaO=None, username=None, admin=None, izdelki=izdelki, idRandIzdelek=randIzdelek[0], imeRandIzdelek=randIzdelek[1])
        else:
            admin = is_admin(username)
            return template('zacetna_stran.html', kategorije=kategorije, napakaO="Vnesili ste napačno geslo.", username=username, admin=admin, izdelki=izdelki, idRandIzdelek=randIzdelek[0], imeRandIzdelek=randIzdelek[1])


def vsebina_kosare():

    """Funkcija za pridobivanje vsebine košarice kot množice."""

    kosara = request.get_cookie('kosara', secret=secret)

    if kosara is None:
        return set()
    try:
        return set(json.loads(kosara))
    except json.JSONDecodeError:
        return set()

# Pomožne funkcije
######################################################################


@get('/static/<filename:path>')
def static(filename):
    return static_file(filename, root='static')


@get('/')
def index():
    username = get_user()
    admin = is_admin(username)
    cur.execute("SELECT * FROM izdelek ORDER BY ocena DESC")
    izdelki = cur.fetchall()
    cur.execute("SELECT id, ime FROM izdelek ORDER BY RANDOM() LIMIT 1")
    randIzdelek = cur.fetchone()
    return template('zacetna_stran.html', kategorije=kategorije, napakaO=None, username=username,
                    admin=admin, izdelki=izdelki, idRandIzdelek=randIzdelek[0], imeRandIzdelek=randIzdelek[1])


@post('/postani_admin')
def postani_admin_post():
    postani_admin()
    redirect('/')


@get('/Login')
def login():
    return template('Login.html', napaka=None)


@post('/Login')
def login_post():
    """Obdelaj izpolnjeno formo za prijavo"""
    # Uporabniško ime, ki ga je uporabnik vpisal v formo
    username = request.forms.username
    # Izračunamo MD5 has gesla, ki ga bomo spravili
    password = password_md5(request.forms.password)
    # Preverimo, ali se je uporabnik pravilno prijavil
    cur.execute("SELECT * FROM uporabnik WHERE username=%s AND password=%s", [username, password])
    if cur.fetchone() is None:
        # Username in geslo se ne ujemata
        return template("Login.html", napaka="Uporabnik ne obstaja", username=username)
    else:
        # Vse je v redu, nastavimo cookie in preusmerimo na glavno stran
        response.set_cookie('username', username, path='/', secret=secret)
        redirect('/')


@get("/Logout")
def logout():
    """Pobriši cookie in preusmeri na login."""
    response.delete_cookie('username')
    redirect('/')


@get('/Register')
def register():
    return template('Register.html', username=None, napaka=None)


@post("/Register")
def register_post():
    print('trying to register')
    """Registriraj novega uporabnika."""
    username = request.forms.username
    password1 = request.forms.password1
    password2 = request.forms.password2
    adminPassword = request.forms.adminPassword
    adminCheck = request.forms.adminCheckbox
    # Ali uporabnik že obstaja?
    cur.execute("SELECT * FROM uporabnik WHERE username=%s", [username])
    if cur.fetchone():
        print('ime že zasedeno')
        # Uporabnik že obstaja
        return template("Register.html", username=username, napaka='To uporabniško ime je že zasedeno.')
    elif not password1 == password2:
        print('gesli se ne ujemata')
        # Geslo se ne ujemata
        return template("Register.html", username=username, napaka='Gesli se ne ujemata.')
    else:
        # Vse je v redu, vstavi novega uporabnika v bazo
        print('ustvarjamo novega uporabnika')

        if adminCheck == "kot admin":
            if adminPassword == adminGeslo:
                print('dodaj admina')

                password = password_md5(password1)
                cur.execute("INSERT INTO uporabnik (username, password, isadmin) VALUES (%s, %s, %s)",
                            (username, password, True))
                # Daj uporabniku cookie
                response.set_cookie('username', username, path='/', secret=secret)
                redirect("/")
            else:
                return template("Register.html", username=username, napaka='Admin geslo ni pravilno.')
        else:
            print('ustvarimo navadnega uporabnika')

            password = password_md5(password1)
            cur.execute("INSERT INTO uporabnik (username, password, isadmin) VALUES (%s, %s, %s)",
                        (username, password, False))
            # Daj uporabniku cookie
            response.set_cookie('username', username, path='/', secret=secret)
            redirect("/")


@post('/')
def iskanje():
    username = get_user()
    admin = is_admin(username)
    search = request.forms.search
    cur.execute("SELECT * FROM izdelek WHERE lower(ime) Like %s OR lower(proizvajalec) Like %s OR lower(kategorija) Like %s",
                ['%' + search + '%', '%' + search + '%', '%' + search + '%'])
    izdelki = cur.fetchall()
    return template('Iskanje.html', napakaO=None, kategorije=kategorije, napaka=None,
                    username=username, admin=admin, izdelki=izdelki)


@get('/kategorije/:x/')
def kategorija(x):
    username = get_user()
    admin = is_admin(username)
    cur.execute("SELECT * FROM izdelek WHERE kategorija=%s", [slovar_kategorij[x]])
    izdelki = cur.fetchall()
    return template('Kategorija.html', x=x, napakaO=None, kategorije=kategorije, napaka=None,
                    username=username, admin=admin, izdelki=izdelki)


@get('/izdelek/:x/')
def izdelek(x):
    username = get_user()
    admin = is_admin(username)
    cur.execute("SELECT id FROM uporabnik WHERE username=%s", [username])
    userid = cur.fetchone()[0]
    cur.execute("SELECT * FROM izdelek WHERE id = %s", [int(x)])
    izdelek = cur.fetchall()
    cur.execute("SELECT * FROM izdelek WHERE proizvajalec=%s AND id!=%s", [izdelek[0][2], int(x)])
    izdelki = cur.fetchall()
    if not izdelki:
        cur.execute("SELECT * FROM izdelek WHERE kategorija=%s AND id!=%s", [izdelek[0][3], int(x)])
        izdelki = cur.fetchall()
    cur.execute("SELECT * FROM zazeljeni WHERE uporabnik = %s AND izdelek = %s", [userid, int(x)])
    najljubsi = cur.fetchall()
    najljubsi = len(najljubsi) == 1
    kosara = vsebina_kosare()

    if len(kosara) == 0:
        vKosari = False
    else:
        vKosari = x in kosara

    return template('Izdelek.html', x=x, napakaO=None, kategorije=kategorije, napaka=None, username=username,
                    admin=admin, izdelek=izdelek, izdelki=izdelki, najljubsi=najljubsi, vKosari=vKosari)


@post('/dodaj_med_zazeljene/:x/')
def dodaj_med_zazeljene(x):
    username = get_user()
    cur.execute("SELECT id FROM uporabnik WHERE username=%s", [username])
    userid = cur.fetchone()[0]
    dodaj = request.forms.dodaj
    if dodaj == "ne":
        cur.execute("DELETE FROM zazeljeni WHERE uporabnik=%s AND izdelek=%s", [userid, int(x)])
    else:
        cur.execute("INSERT INTO zazeljeni (uporabnik, izdelek) VALUES (%s, %s)", [userid, int(x)])
    redirect("/izdelek/{}/".format(x))


@post('/dodaj_v_kosaro/:x/')
def dodaj_v_kosaro(x):
    kosara = vsebina_kosare()
    kosara.symmetric_difference_update({x})  # doda v košaro, če ga še ni, sicer ga odstrani
    response.set_cookie('kosara', json.dumps(list(kosara)), path='/', secret=secret)
    redirect("/izdelek/{}/".format(x))


@get('/kosara')
def kosara():
    username = get_user()
    admin = is_admin(username)
    kosara = vsebina_kosare()
    izdelki = []

    if len(kosara) == 0:
        napaka = 'Vaša košarica je prazna.'
        izrisi = False
    else:
        napaka = None
        izrisi = True
        cur.execute("SELECT * FROM izdelek WHERE id IN ({})".format(", ".join("%s" for _ in kosara)), tuple(kosara))
        izdelki = cur.fetchall()

    brez_popusta = 0
    z_popustom = 0

    for i in izdelki:
        brez_popusta += i[6]
        z_popustom += i[6]*(100-i[5])/100

    return template('kosara.html', izrisi=izrisi, napakaO=None, napaka=napaka, username=username, kategorije=kategorije,
                    izdelki=izdelki, admin=admin, stevilo_izdelkov=len(izdelki), brez_popusta=brez_popusta, z_popustom=z_popustom)


@get('/nakup')
def nakup():
    username = get_user()
    admin = is_admin(username)
    kosara = vsebina_kosare()

    cur.execute("SELECT * FROM izdelek WHERE id IN ({})".format(", ".join("%s" for _ in kosara)), tuple(kosara))
    izdelki = cur.fetchall()

    brez_popusta = 0
    z_popustom = 0

    for i in izdelki:
        brez_popusta += i[6]
        z_popustom += i[6] * (100 - i[5]) / 100

    return template('nakup.html', napakaO=None, napaka=None, username=username, kategorije=kategorije,
                    izdelki=izdelki, admin=admin, stevilo_izdelkov=len(izdelki), brez_popusta=brez_popusta, z_popustom=z_popustom)


@post('/nakup')
def nakup_post():
    username = get_user()
    cur.execute("SELECT id FROM uporabnik WHERE username=%s", [username])
    userid = cur.fetchone()[0]
    cur.execute("INSERT INTO nakup (nacin_placila, uporabnik_id) VALUES (%s, %s)", [request.forms.nacin_placila, userid])
    cur.execute("SELECT * FROM nakup WHERE uporabnik_id=%s ORDER BY stevilka_racuna DESC", [userid])
    stevilka_racuna = cur.fetchone()[0]

    kosara = vsebina_kosare()

    for str in kosara:   # to se pomoje da optimizirat da nimamo toliko sql poizvedb
        id_izdelka = str.strip(' ')
        cur.execute("SELECT cena, popust FROM izdelek WHERE id=%s", [id_izdelka])
        cena_in_popust = cur.fetchone()
        trenutna_cena_izdelka = cena_in_popust[0] * (100-cena_in_popust[1])/100
        cur.execute("INSERT INTO kupljeni_izdelki (stevilka_racuna, id_izdelka, cena_ob_nakupu) VALUES (%s, %s, %s)",
                    [stevilka_racuna, id_izdelka, trenutna_cena_izdelka])

    response.delete_cookie('kosara', path='/', secret=secret)
    redirect("/")

@get('/zazeljeni')
def zazeljeni_get():
    username = get_user()
    admin = is_admin(username)
    cur.execute("SELECT id FROM uporabnik WHERE username=%s", [username])
    userid = cur.fetchone()[0]
    cur.execute("SELECT * FROM zazeljeni WHERE uporabnik=%s", [userid])
    zazelj = cur.fetchall()
    izdelki = []

    if not zazelj:
        napaka = 'Nimate še dodanih zaželjenih izdelkov.'
        izrisi = False
    else:
        napaka = None
        izrisi = True
        cur.execute("SELECT t.id, t.ime, t.proizvajalec, t.kategorija, t.ocena, t.popust, t.cena FROM izdelek AS t JOIN zazeljeni AS n ON (t.id = n.izdelek) WHERE n.uporabnik=%s", [userid])
        izdelki = cur.fetchall()

    return template('zazeljeni.html', izrisi=izrisi, napakaO=None, napaka=napaka, username=username, kategorije=kategorije,
                    izdelki=izdelki, admin=admin)


@get('/uredi_izdelek/:x/')
def uredi_izdelek(x):
    username = get_user()
    admin = is_admin(username)
    cur.execute("SELECT * FROM izdelek WHERE id = %s", [int(x)])
    podatki = cur.fetchall()
    return template('uredi_izdelek.html', id=int(x), ime=podatki[0][1], proizvajalec=podatki[0][2], kategorija=podatki[0][3],
                    ocena=podatki[0][4], popust=podatki[0][5], cena=podatki[0][6], kategorije=kategorije, x=x,
                    napakaO=None, napaka=None, username=username, admin=admin)


@post('/uredi_izdelek/:x/')
def uredi_izdelek_post(x):
    username = get_user()
    admin = is_admin(username)
    ime = request.forms.ime
    proizvajalec = request.forms.proizvajalec
    kategorija = request.forms.kategorija
    ocena = request.forms.ocena
    popust = request.forms.popust
    cena = request.forms.cena
    try:
        cur.execute("UPDATE izdelek SET ime=%s, proizvajalec=%s, kategorija=%s, ocena=%s, popust=%s, cena=%s WHERE id=%s",
                    [ime, proizvajalec, kategorija, ocena, popust, cena, int(x)])
        conn.commit()
    except Exception as ex:
        cur.execute("SELECT * FROM izdelek WHERE id = %s", [int(x)])
        podatki = cur.fetchall()
        return template('uredi_izdelek.html', id=int(x), ime=podatki[0][1], proizvajalec=podatki[0][2],
                        kategorija=podatki[0][3],
                        ocena=podatki[0][4], popust=podatki[0][5], cena=podatki[0][6], kategorije=kategorije, x=x,
                        napakaO=None, napaka='Zgodila se je napaka: %s' % ex, username=username, admin=admin)
    redirect("/izdelek/{}/".format(x))


######################################################################
# Glavni program

# priklopimo se na bazo
conn = psycopg2.connect(database=auth.db, host=auth.host, user=auth.user, password=auth.password)
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)    # onemogočimo transakcije
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# poženemo strežnik na portu 8080, glej http://localhost:8000/
run(host='localhost', port=8000, reloader=True)
