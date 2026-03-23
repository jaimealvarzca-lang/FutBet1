import os
import re
import math
import time
import random
import requests
import telebot
from telebot import types
from datetime import date, datetime, timezone
from flask import Flask
from threading import Thread

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "Falta el secreto TELEGRAM_TOKEN. "
        "Añádelo en la pestaña Secrets del panel izquierdo."
    )

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ---------------------------------------------------------------------------
# Flask keep-alive
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot vivo y funcionando!"

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# SofaScore API
# ---------------------------------------------------------------------------
SF_BASE = "https://api.sofascore.com/api/v1"
SF_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.sofascore.com/',
    'Origin': 'https://www.sofascore.com',
}

# (display_name, uniqueTournament ID on SofaScore)
LIGAS = [
    ("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",    17),
    ("🇪🇸 La Liga",                   8),
    ("🇮🇹 Serie A",                   23),
    ("🇩🇪 Bundesliga",                35),
    ("🇫🇷 Ligue 1",                   34),
    ("⚽ Champions League",            7),
    ("🇵🇹 Liga Portugal",            238),
    ("🇳🇱 Eredivisie",               37),
    ("🇧🇷 Brasileirao",             325),
    ("🇦🇷 Liga Profesional",        155),
    ("🇲🇽 Liga MX",                 352),
    ("🇺🇸 MLS",                     242),
]

# ---------------------------------------------------------------------------
# Star players per team (for shot-on-target tips)
# ---------------------------------------------------------------------------
# Each team maps to a list of (player_name, position_key) tuples.
# position_key selects from LINEAS_POR_POSICION below.
JUGADORES_ESTRELLA = {
    # ── Premier League ──────────────────────────────────────────────────────
    "Manchester City": [
        ("Haaland",         "delantero"),
        ("Foden",           "mediapunta"),
        ("Doku",            "extremo"),
        ("Savinho",         "extremo"),
        ("Bernardo Silva",  "mediocentro_ofensivo"),
        ("Gvardiol",        "extremo"),
    ],
    "Arsenal": [
        ("Saka",            "extremo"),
        ("Martinelli",      "extremo"),
        ("Havertz",         "delantero"),
        ("Ødegaard",        "mediapunta"),
        ("Trossard",        "extremo"),
        ("Gyokeres",          "delantero"),
    ],
    "Liverpool": [
        ("Salah",           "extremo"),
        ("Ekitike",    "delantero"),
        ("Gakpo",           "extremo"),
        ("Szoboszlai",      "mediapunta"),
        ("Mac Allister",    "mediocentro_ofensivo"),
    ],
    "Chelsea": [
        ("Palmer",          "mediapunta"),
        ("Joao Pedro",      "delantero"),
        ("Garnacho",          "extremo"),
        ("Enzo Fernández",  "mediocentro_ofensivo"),
        ("Mudryk",          "extremo"),
    ],
    "Tottenham": [
        ("Xavi Simons",      "Mediocentro_ofensivo"),
        ("Solanke",         "delantero"),
        ("Maddison",        "mediapunta"),
        ("Kolo Muani",         "delantero"),
        ("Richarlison",     "delantero"),
        ("Bergvall",        "mediocentro_ofensivo"),
    ],
    "Manchester United": [
        ("Sesko",         "delantero"),
        ("Fernandes",       "mediapunta"),
        ("Cunha",        "extremo"),
        ("Mbeumo",         "delantero"),
        ("Mount",           "mediocentro_ofensivo"),
        ("Mainoo",          "mediocentro_ofensivo"),
    ],
    "Newcastle": [
        ("Elanga",            "delantero"),
        ("Gordon",          "extremo"),
        ("Joelinton",       "mediocentro_ofensivo"),
        ("Tonali",          "mediocentro_ofensivo"),
        ("Bruno Guimarães", "mediocentro_ofensivo"),
        ("Murphy",          "extremo"),
        ("Woltemade",        "extremo"),
    ],
    "Aston Villa": [
        ("Watkins",         "delantero"),
        ("Bailey",          "extremo"),
        ("Duran",           "delantero"),
        ("Tielemans",       "mediocentro_ofensivo"),
        ("Diaby",           "extremo"),
        ("McGinn",          "mediocentro_ofensivo"),
        ("Rogers",          "extremo"),
    ],
    # ── La Liga ─────────────────────────────────────────────────────────────
    "Real Madrid": [
        ("Vinicius Jr.",    "extremo"),
        ("Mbappé",          "delantero"),
        ("Bellingham",      "mediapunta"),
        ("Rodrygo",         "extremo"),
        ("Valverde",        "mediocentro_ofensivo"),
        ("Brahim Díaz",     "mediapunta"),
        ("Güler",           "mediapunta"),
    ],
    "Barcelona": [
        ("Lewandowski",     "delantero"),
        ("Yamal",           "extremo"),
        ("Raphinha",        "extremo"),
        ("Pedri",           "mediapunta"),
        ("Dani Olmo",       "mediapunta"),
        ("Fermín",          "mediocentro_ofensivo"),
        ("Gavi",            "mediocentro_ofensivo"),
    ],
    "Atletico Madrid": [
        ("Griezmann",       "segunda_punta"),
        ("Julián Álvarez",  "delantero"),
        ("Sørloth",         "delantero"),
        ("Lookman",          "extremo"),
        ("Barrios",         "mediocentro_ofensivo"),
        ("Llorente",        "mediocentro_ofensivo"),
        ("Baena",       "mediocentro_ofensivo"),
    ],
    "Athletic Club": [
        ("Williams",        "extremo"),
        ("Nico Williams",   "extremo"),
        ("Guruzeta",        "delantero"),
        ("Sancet",          "mediapunta"),
        ("Berenguer",       "extremo"),
        ("Vesga",           "mediocentro_ofensivo"),
    ],
    "Real Sociedad": [
        ("Oyarzabal",       "delantero"),
        ("Take Kubo",       "extremo"),
        ("Brais Méndez",    "mediapunta"),
        ("Sucic",           "mediapunta"),
        ("Barrenetxea",     "extremo"),
        ("Oskarsson",          "delantero"),
        ("Zubimendi",       "mediocentro_ofensivo"),
    ],
    "Villarreal": [
        ("Moleiro",     "extremo"),
        ("Pepe",         "extremo"),
        ("Pedraza",         "extremo"),
        ("Mikautadze",         "extremo"),
        ("Terrats",         "mediocentro_ofensivo"),
    ],
    "Sevilla": [
        ("Lukebakio",       "extremo"),
        ("Isaac Romero",    "delantero"),
        ("Sow",             "mediocentro_ofensivo"),
        ("Juanlu",          "extremo"),
        ("Ejuke",           "extremo"),
        ("Ramos",           "mediocentro_ofensivo"),
        ("Saúl",            "mediocentro_ofensivo"),
    ],
    # ── Serie A ─────────────────────────────────────────────────────────────
    "Inter": [
        ("Lautaro",         "delantero"),
        ("Thuram",          "delantero"),
        ("Calhanoglu",      "mediapunta"),
        ("Barella",         "mediocentro_ofensivo"),
        ("Dimarco",         "extremo"),
        ("Mkhitaryan",      "mediocentro_ofensivo"),
        ("Correa",          "delantero"),
    ],
    "AC Milan": [
        ("Leão",            "extremo"),
        ("Nkunku",          "delantero"),
        ("Pulisic",         "extremo"),
        ("Reijnders",       "mediocentro_ofensivo"),
        ("Theo Hernández",  "extremo"),
        ("Chukwueze",       "extremo"),
        ("Abraham",         "delantero"),
    ],
    "Juventus": [
        ("Vlahovic",        "delantero"),
        ("Yildiz",          "mediapunta"),
        ("Nico González",   "extremo"),
        ("Mbangula",        "extremo"),
        ("Conceiçao",       "extremo"),
        ("Koopmeiners",     "mediocentro_ofensivo"),
        ("Weah",            "extremo"),
    ],
    "Napoli": [
        ("Lukaku",          "delantero"),
        ("Politano",        "extremo"),
        ("Raspadori",       "segunda_punta"),
        ("McTominay",       "mediocentro_ofensivo"),
        ("Ngonge",          "extremo"),
        ("Neres",           "extremo"),
    ],
    "Roma": [
        ("Dybala",          "segunda_punta"),
        ("Dovbyk",          "delantero"),
        ("El Shaarawy",     "extremo"),
        ("Pellegrini",      "mediapunta"),
        ("Baldanzi",        "mediapunta"),
        ("Soulé",           "mediapunta"),
        ("Pisilli",         "mediocentro_ofensivo"),
    ],
    "Lazio": [
        ("Immobile",        "delantero"),
        ("Castellanos",     "delantero"),
        ("Zaccagni",        "extremo"),
        ("Isaksen",         "extremo"),
        ("Guendouzi",       "mediocentro_ofensivo"),
        ("Pedro",           "segunda_punta"),
        ("Dia",             "delantero"),
    ],
    "Atalanta": [
        ("Lookman",         "extremo"),
        ("De Ketelaere",    "mediapunta"),
        ("Retegui",         "delantero"),
        ("Ederson",         "mediocentro_ofensivo"),
        ("Zappacosta",      "extremo"),
        ("Bellanova",       "extremo"),
        ("Pasalic",         "mediocentro_ofensivo"),
    ],
    "Fiorentina": [
        ("Kean",            "delantero"),
        ("Colpani",         "extremo"),
        ("Adli",            "mediapunta"),
        ("Sottil",          "extremo"),
        ("Gudmundsson",     "mediapunta"),
        ("Beltran",         "segunda_punta"),
        ("Biraghi",         "extremo"),
    ],
    # ── Bundesliga ──────────────────────────────────────────────────────────
    "Bayern Munich": [
        ("Kane",            "delantero"),
        ("Musiala",         "mediapunta"),
        ("Karl",            "extremo"),
        ("Olise",           "extremo"),
        ("Gnabry",          "extremo"),
        ("Coman",           "extremo"),
        ("Müller",          "segunda_punta"),
    ],
    "Borussia Dortmund": [
        ("Guirassy",        "delantero"),
        ("Brandt",          "mediapunta"),
        ("Gittens",         "extremo"),
        ("Adeyemi",         "extremo"),
        ("Nmecha",          "delantero"),
        ("Beier",           "delantero"),
        ("Sabitzer",        "mediocentro_ofensivo"),
    ],
    "Bayer Leverkusen": [
        ("Boniface",        "delantero"),
        ("Grimaldo",        "extremo"),
        ("Hofmann",         "extremo"),
        ("Tella",           "extremo"),
    ],
    "RB Leipzig": [
        ("Openda",          "delantero"),
        ("Nusa",            "extremo"),
        ("Baumgartner",     "mediocentro_ofensivo"),
        ("Poulsen",         "delantero"),
        ("Raum",            "extremo"),
    ],
    "Eintracht Frankfurt": [
        ("Ekitike",         "delantero"),
        ("Uzun",            "extremo"),
        ("Götze",           "mediapunta"),
        ("Larsson",         "extremo"),
        ("Marmoush",        "delantero"),
        ("Chaibi",          "mediapunta"),
        ("Kristensen",      "extremo"),
    ],
    # ── Ligue 1 ─────────────────────────────────────────────────────────────
    "Paris Saint-Germain": [
        ("Dembélé",         "extremo"),
        ("Barcola",         "extremo"),
        ("Kvaratskhelia",   "extremo"),
        ("Vitinha",         "mediocentro_ofensivo"),
        ("Fabián Ruiz",     "mediocentro_ofensivo"),
        ("Joao Neves",     "mediapunta"),
        ("Doue",   "delantero"),
    ],
    "Monaco": [
        ("Embolo",          "delantero"),
        ("Akliouche",       "mediapunta"),
        ("Minamino",        "mediapunta"),
        ("Golovin",         "mediapunta"),
        ("Balogun",         "delantero"),
        ("Camara",          "mediocentro_ofensivo"),
        ("Ben Seghir",      "mediapunta"),
    ],
    "Marseille": [
        ("Greenwood",       "extremo"),
        ("Moumbagna",       "delantero"),
        ("Rabiot",          "mediocentro_ofensivo"),
        ("Harit",           "mediapunta"),
        ("De la Fuente",    "extremo"),
        ("Wahi",            "delantero"),
        ("Luis Henrique",   "extremo"),
    ],
    "Lyon": [
        ("Lacazette",       "delantero"),
        ("Nuamah",          "extremo"),
        ("Fofana",          "mediocentro_ofensivo"),
        ("Tolisso",         "mediocentro_ofensivo"),
        ("Orban",           "delantero"),
        ("Benrahma",        "extremo"),
        ("Caqueret",        "mediocentro_ofensivo"),
    ],
    "Lille": [
        ("David",           "delantero"),
        ("Zhegrova",        "extremo"),
        ("Angel Gomes",     "mediapunta"),
        ("Haraldsson",      "extremo"),
        ("Cabella",         "mediapunta"),
        ("Mukau",           "extremo"),
        ("Sahraoui",        "mediapunta"),
    ],
}

# Tips available per position type
LINEAS_POR_POSICION = {
    "delantero": [
        "1+ remate a puerta",
        "2+ remates a puerta",
        "2+ remates totales",
        "3+ remates totales",
        "anotar en el partido",
        "1+ remate en el área",
        "recibir 1+ falta",
    ],
    "extremo": [
        "1+ remate a puerta",
        "2+ remates totales",
        "recibir 2+ faltas",
        "recibir 3+ faltas",
        "completar 2+ regates con éxito",
        "completar 3+ regates con éxito",
        "anotar o asistir en el partido",
        "1+ remate en el área",
    ],
    "mediapunta": [
        "1+ remate a puerta",
        "2+ remates totales",
        "dar 1+ asistencia",
        "recibir 2+ faltas",
        "implicarse en un gol (gol o asistencia)",
        "completar 2+ regates con éxito",
        "anotar en el partido",
    ],
    "segunda_punta": [
        "1+ remate a puerta",
        "2+ remates totales",
        "anotar en el partido",
        "recibir 2+ faltas",
        "dar 1+ asistencia",
        "implicarse en un gol (gol o asistencia)",
    ],
    "mediocentro_ofensivo": [
        "cometer 2+ faltas",
        "recibir 1+ falta",
        "1+ remate a puerta",
        "2+ remates totales",
        "dar 1+ asistencia",
        "completar 1+ pase clave",
        "cometer 1+ falta",
    ],
}


# ---------------------------------------------------------------------------
# Goalkeeper database — (starter, backup) per team
# ---------------------------------------------------------------------------
PORTEROS = {
    # ── Premier League ──────────────────────────────────────────────────────
    "Manchester City":    ("Ederson",        "Ortega"),
    "Arsenal":            ("Raya",           "Neto"),
    "Liverpool":          ("Alisson",        "Kelleher"),
    "Chelsea":            ("Sánchez",        "Petrovic"),
    "Tottenham":          ("Vicario",        "Forster"),
    "Manchester United":  ("Onana",          "Bayindir"),
    "Newcastle":          ("Pope",           "Dubravka"),
    "Aston Villa":        ("Martínez",       "Olsen"),
    # ── La Liga ─────────────────────────────────────────────────────────────
    "Real Madrid":        ("Courtois",       "Lunin"),
    "Barcelona":          ("Ter Stegen",     "Iñaki Peña"),
    "Atletico Madrid":    ("Oblak",          "Musso"),
    "Athletic Club":      ("Unai Simón",     "Agirrezabala"),
    "Real Sociedad":      ("Remiro",         "Zubikarai"),
    "Villarreal":         ("Díaz",           "Reina"),
    "Sevilla":            ("Dmitrović",      "Bono"),
    # ── Serie A ─────────────────────────────────────────────────────────────
    "Inter":              ("Sommer",         "Di Gennaro"),
    "AC Milan":           ("Maignan",        "Sportiello"),
    "Juventus":           ("Szczesny",       "Perin"),
    "Napoli":             ("Meret",          "Caprile"),
    "Roma":               ("Svilar",         "Ryan"),
    "Lazio":              ("Provedel",       "Mandas"),
    "Atalanta":           ("Carnesecchi",    "Rossi"),
    "Fiorentina":         ("De Gea",         "Terracciano"),
    # ── Bundesliga ──────────────────────────────────────────────────────────
    "Bayern Munich":      ("Neuer",          "Ulreich"),
    "Borussia Dortmund":  ("Kobel",          "Meyer"),
    "Bayer Leverkusen":   ("Hradecky",       "Flekken"),
    "RB Leipzig":         ("Blaswich",       "Gulacsi"),
    "Eintracht Frankfurt":("Trapp",          "Kaua Santos"),
    # ── Ligue 1 ─────────────────────────────────────────────────────────────
    "Paris Saint-Germain":("Donnarumma",     "Safonov"),
    "Monaco":             ("Köhn",           "Majecki"),
    "Marseille":          ("Pau López",      "Ngapandouetnbu"),
    "Lyon":               ("Lopes",          "Perri"),
    "Lille":              ("Chevalier",      "Porte"),
}

LINEAS_PORTERO = [
    "3+ paradas en el partido",
    "4+ paradas en el partido",
    "2+ paradas en el partido",
    "mantener la portería a cero",
    "5+ paradas en el partido",
    "parar 1+ tiro difícil",
    "ser el mejor jugador de su equipo",
]


def get_tiro_jugador(home_name, away_name):
    """Return an occasional player or goalkeeper tip (≈40% chance).

    30% of the time it's a goalkeeper tip, 70% an outfield player tip.
    """
    if random.random() > 0.40:
        return None

    # Decide goalkeeper vs outfield player (30/70 split)
    if random.random() < 0.30:
        # Goalkeeper tip
        gk_candidatos = []
        for team in (home_name, away_name):
            if team in PORTEROS:
                titular, suplente = PORTEROS[team]
                gk_candidatos.append((team, titular))
                gk_candidatos.append((team, suplente))
        if gk_candidatos:
            equipo, portero = random.choice(gk_candidatos)
            linea = random.choice(LINEAS_PORTERO)
            return f"🧤 <b>Portero destacado:</b> {h(portero)} ({h(equipo)}) — {linea}"

    # Outfield player tip
    candidatos = []
    for team in (home_name, away_name):
        if team in JUGADORES_ESTRELLA:
            for jugador, pos in JUGADORES_ESTRELLA[team]:
                candidatos.append((team, jugador, pos))

    if not candidatos:
        return None

    equipo, jugador, pos = random.choice(candidatos)
    lineas = LINEAS_POR_POSICION.get(pos, LINEAS_POR_POSICION["delantero"])
    linea = random.choice(lineas)
    return f"🎯 <b>Jugador destacado:</b> {h(jugador)} ({h(equipo)}) — {linea}"

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def h(text):
    """Escape text for Telegram HTML mode."""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))

# ---------------------------------------------------------------------------
# SofaScore data helpers
# ---------------------------------------------------------------------------
def sf_get(path):
    try:
        r = requests.get(f"{SF_BASE}{path}", headers=SF_HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# FlashScore integration — team form
# ---------------------------------------------------------------------------
FS_SEARCH_URL = "https://s.flashscore.com/search/"
FS_FEED_BASE  = "https://d.flashscore.com/x/feed"
FS_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/122.0.0.0 Safari/537.36'),
    'x-fsign': 'SW9D1eZo',
    'Accept': '*/*',
    'Referer': 'https://www.flashscore.com/',
    'Origin': 'https://www.flashscore.com',
}
_fs_id_cache: dict = {}


def _fs_parse(text):
    """Parse FlashScore ¬/~ delimited feed into a list of field dicts."""
    result = []
    for segment in text.split('~'):
        segment = segment.strip('¬ \n')
        if not segment:
            continue
        rec = {}
        for part in segment.split('¬'):
            if '÷' in part:
                k, _, v = part.partition('÷')
                rec[k.strip()] = v.strip()
        if rec:
            result.append(rec)
    return result


def _fs_team_id(name):
    """Return FlashScore team ID for a given team name, or None."""
    if name in _fs_id_cache:
        return _fs_id_cache[name]
    try:
        r = requests.get(
            FS_SEARCH_URL,
            params={'q': name, 'l': '1', 's': '2', 'f': '1;1', 'pid': '2', 'sid': '1'},
            headers=FS_HEADERS, timeout=8
        )
        best_id, best_score = None, -1
        for rec in _fs_parse(r.text):
            # AC=1 means football team
            if rec.get('AC') not in ('1', None):
                continue
            fs_id   = rec.get('AA', '')
            fs_name = rec.get('AH', '')
            if not fs_id or not fs_name:
                continue
            nl, fl = name.lower(), fs_name.lower()
            if nl == fl or nl in fl or fl in nl:
                score = len(min(nl, fl, key=len))
                if score > best_score:
                    best_score, best_id = score, fs_id
        _fs_id_cache[name] = best_id
        return best_id
    except Exception as ex:
        print(f"[FS] search error ({name}): {ex}")
        return None


def _fs_team_form(name, n=5):
    """Return list of n form icons from FlashScore, oldest→newest. None on failure."""
    fs_id = _fs_team_id(name)
    if not fs_id:
        return None
    try:
        url = f"{FS_FEED_BASE}/proxy-local-tab-team-matches;id={fs_id};type=last/0/1"
        r = requests.get(url, headers=FS_HEADERS, timeout=8)
        raw = r.text

        icons = []
        for rec in _fs_parse(raw):
            if len(icons) >= n:
                break
            # AW = winner code: '1'=home won, '2'=away won, '0'=draw
            winner = rec.get('AW')
            if winner is None:
                continue
            # Determine whether our team was home or away.
            # Field U1 or AB typically holds the home team's FlashScore ID.
            home_fs_id = rec.get('U1') or rec.get('AB') or rec.get('T1')
            if home_fs_id:
                is_home = (home_fs_id == fs_id)
            else:
                # Can't determine position; try matching home team name in AH
                home_name = rec.get('AH') or rec.get('CL') or ''
                is_home = (name.lower() in home_name.lower()) if home_name else None

            if winner == '0':
                icons.append('🟠')
            elif winner == '1':   # home team won
                if is_home is None:
                    icons.append('🟢')   # unknown position, guess
                else:
                    icons.append('🟢' if is_home else '🔴')
            elif winner == '2':   # away team won
                if is_home is None:
                    icons.append('🟢')
                else:
                    icons.append('🔴' if is_home else '🟢')

        icons.reverse()   # oldest → most recent
        return icons if icons else None
    except Exception as ex:
        print(f"[FS] form error ({name}/{fs_id}): {ex}")
        return None


def get_events_by_league(tournament_id):
    hoy = str(date.today())
    data = sf_get(f"/sport/football/scheduled-events/{hoy}")
    events = data.get('events', [])
    return [
        e for e in events
        if e.get('tournament', {}).get('uniqueTournament', {}).get('id') == tournament_id
    ]


def get_yesterday_events_by_league(tournament_id):
    from datetime import timedelta
    ayer = str(date.today() - timedelta(days=1))
    data = sf_get(f"/sport/football/scheduled-events/{ayer}")
    events = data.get('events', [])
    return [
        e for e in events
        if e.get('tournament', {}).get('uniqueTournament', {}).get('id') == tournament_id
        and e.get('status', {}).get('type') in ('finished', 'canceled', 'postponed')
    ]


def get_event_statistics(event_id):
    data = sf_get(f"/event/{event_id}/statistics")
    return data.get('statistics', [])


def get_stat_total(statistics, keyword):
    """Return (home_val, away_val) for a given stat keyword from the ALL period."""
    for period in statistics:
        if period.get('period') == 'ALL':
            for group in period.get('groups', []):
                for item in group.get('statisticsItems', []):
                    if keyword.lower() in item.get('name', '').lower():
                        try:
                            hv = int(str(item.get('home', 0) or 0).split('.')[0])
                            av = int(str(item.get('away', 0) or 0).split('.')[0])
                            return hv, av
                        except Exception:
                            pass
    return None, None


def get_vote(event_id):
    data = sf_get(f"/event/{event_id}/vote")
    vote = data.get('vote', {})
    v1 = float(vote.get('vote1', 0) or 0)
    vx = float(vote.get('voteX', 0) or 0)
    v2 = float(vote.get('vote2', 0) or 0)
    total = v1 + vx + v2
    if total > 0:
        return {
            'home': round(v1 / total * 100, 1),
            'draw': round(vx / total * 100, 1),
            'away': round(v2 / total * 100, 1),
        }
    return None


def get_odds(event_id):
    return sf_get(f"/event/{event_id}/odds/1/all")


def find_market(odds_data, *keywords):
    for m in odds_data.get('markets', []):
        name = m.get('marketName', '').lower()
        if all(kw.lower() in name for kw in keywords):
            return m.get('choices', [])
    return []


def get_choice_odd(choices, name, handicap=None):
    for c in choices:
        c_name = c.get('name', '').lower()
        c_handicap = str(c.get('handicap', '') or '').strip()
        if handicap is not None:
            if c_name == name.lower() and c_handicap == str(handicap):
                return c
            if c_name == f"{name.lower()} {handicap}":
                return c
        else:
            if c_name == name.lower():
                return c
    return None


def odd_to_prob(choice):
    if not choice:
        return None
    try:
        val = float(choice.get('fractionalValue') or choice.get('value') or 0)
        if val > 1:
            return round(1 / val * 100, 1)
    except Exception:
        pass
    return None


def normalize2(p1, p2):
    if p1 is not None and p2 is not None:
        total = p1 + p2
        if total > 0:
            return round(p1 / total * 100, 1), round(p2 / total * 100, 1)
    return p1, p2


def normalize3(p1, px, p2):
    vals = [p1 or 0, px or 0, p2 or 0]
    total = sum(vals)
    if total > 0:
        return [round(v / total * 100, 1) for v in vals]
    return vals


# ---------------------------------------------------------------------------
# Statistical prediction engine (Poisson-based fallback)
# ---------------------------------------------------------------------------
def _poisson(mu, k):
    """P(X = k) for Poisson distribution with mean mu."""
    if mu <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-mu) * (mu ** k) / math.factorial(k)


def _poisson_over_under(mu, line):
    """Return (p_over, p_under) as percentages for a given Poisson mean and line."""
    k_max = int(line)
    p_under = sum(_poisson(mu, k) for k in range(k_max + 1))
    p_over = 1.0 - p_under
    total = p_over + p_under
    return round(p_over / total * 100, 1), round(p_under / total * 100, 1)


def _1x2_poisson(home_xg, away_xg):
    """Compute 1X2 probabilities from expected goals via Poisson."""
    pw, pd, pa = 0.0, 0.0, 0.0
    for h in range(9):
        for a in range(9):
            p = _poisson(home_xg, h) * _poisson(away_xg, a)
            if h > a:
                pw += p
            elif h == a:
                pd += p
            else:
                pa += p
    total = pw + pd + pa
    if total <= 0:
        return 40.0, 30.0, 30.0
    return round(pw / total * 100, 1), round(pd / total * 100, 1), round(pa / total * 100, 1)


def get_team_form_stats(team_id):
    """Return (avg_goals_scored, avg_goals_conceded) from last 10 finished matches."""
    data = sf_get(f"/team/{team_id}/events/last/0")
    events = [
        e for e in data.get('events', [])
        if e.get('status', {}).get('type') == 'finished'
    ][:10]

    if not events:
        return 1.3, 1.1

    scored, conceded = [], []
    for e in events:
        home_id = e.get('homeTeam', {}).get('id')
        hs = int(e.get('homeScore', {}).get('current', 0) or 0)
        as_ = int(e.get('awayScore', {}).get('current', 0) or 0)
        if home_id == team_id:
            scored.append(hs)
            conceded.append(as_)
        else:
            scored.append(as_)
            conceded.append(hs)

    avg_s = round(sum(scored) / len(scored), 2) if scored else 1.3
    avg_c = round(sum(conceded) / len(conceded), 2) if conceded else 1.1
    return avg_s, avg_c


CORNER_LINES = [7.5, 8.5, 9.5, 10.5, 11.5]
YELLOW_LINES = [2.5, 3.5, 4.5, 5.5]
GOAL_LINES   = [1.5, 2.5, 3.5]


def pick_best_line(mu, candidate_lines):
    """Pick the line from candidates that gives the most confident over/under call.

    Targets the line whose probability for the more likely side is closest to
    65% — decisive enough to be a real pick, but not a trivial extreme.
    """
    TARGET = 65.0
    best_line = candidate_lines[0]
    best_diff = float('inf')
    for line in candidate_lines:
        p_over, p_under = _poisson_over_under(mu, line)
        conf = max(p_over, p_under)
        diff = abs(conf - TARGET)
        if diff < best_diff:
            best_diff = diff
            best_line = line
    return best_line


def calc_stat_predictions(event):
    """Calculate full match predictions from team form using Poisson model."""
    home_id = event.get('homeTeam', {}).get('id')
    away_id = event.get('awayTeam', {}).get('id')

    hs, hc = get_team_form_stats(home_id)
    as_, ac = get_team_form_stats(away_id)

    # Expected goals: blend of attack vs opponent defence
    home_xg = max(0.3, (hs + ac) / 2)
    away_xg = max(0.3, (as_ + hc) / 2)
    total_xg = home_xg + away_xg

    # 1X2
    p1, px, p2 = _1x2_poisson(home_xg, away_xg)

    # Goals — pick best line
    goal_line = pick_best_line(total_xg, GOAL_LINES)
    go, gu = _poisson_over_under(total_xg, goal_line)

    # BTTS
    p_h_scores = 1 - _poisson(home_xg, 0)
    p_a_scores = 1 - _poisson(away_xg, 0)
    btts_yes = round(p_h_scores * p_a_scores * 100, 1)
    btts_no = round(100 - btts_yes, 1)

    # Corners — expected ~ 7.5 + xG; pick best line
    corner_mu = max(7.0, 7.5 + total_xg * 1.0)
    corner_line = pick_best_line(corner_mu, CORNER_LINES)
    co, cu = _poisson_over_under(corner_mu, corner_line)

    # Yellow cards — pick best line; base avg ~3.8 modulated by game intensity
    yellow_mu = max(2.0, 2.5 + total_xg * 0.35)
    yellow_line = pick_best_line(yellow_mu, YELLOW_LINES)
    yo, yu = _poisson_over_under(yellow_mu, yellow_line)

    return {
        '1x2':    {'home': p1, 'draw': px, 'away': p2},
        'goals':  {'over': go, 'under': gu, 'line': goal_line},
        'btts':   {'yes': btts_yes, 'no': btts_no},
        'corners':{'over': co, 'under': cu, 'line': corner_line},
        'yellows':{'over': yo, 'under': yu, 'line': yellow_line},
    }


def get_predictions(event):
    """Return predictions for a match, using odds first, then Poisson fallback."""
    event_id = event['id']
    vote = get_vote(event_id)
    odds = get_odds(event_id)
    result = {}

    # ---- 1X2 ----
    if vote:
        result['1x2'] = vote
    else:
        choices = find_market(odds, 'full time') or find_market(odds, '1x2')
        p1 = odd_to_prob(get_choice_odd(choices, '1'))
        px = odd_to_prob(get_choice_odd(choices, 'X'))
        p2 = odd_to_prob(get_choice_odd(choices, '2'))
        if p1 and px and p2:
            p1, px, p2 = normalize3(p1, px, p2)
            result['1x2'] = {'home': p1, 'draw': px, 'away': p2}
        else:
            result['1x2'] = None

    # ---- Goals Over/Under 2.5 ----
    goal_choices = []
    for kws in [('total goals',), ('goals', 'over'), ('over/under',)]:
        goal_choices = find_market(odds, *kws)
        if goal_choices:
            break
    go_c = get_choice_odd(goal_choices, 'Over', '2.5') or get_choice_odd(goal_choices, 'Over 2.5')
    gu_c = get_choice_odd(goal_choices, 'Under', '2.5') or get_choice_odd(goal_choices, 'Under 2.5')
    go = odd_to_prob(go_c)
    gu = odd_to_prob(gu_c)
    if go and gu:
        go, gu = normalize2(go, gu)
        result['goals'] = {'over': go, 'under': gu, 'line': 2.5}
    else:
        result['goals'] = None   # filled by fallback below

    # ---- BTTS ----
    btts_choices = []
    for kws in [('both teams to score',), ('btts',), ('ambos',)]:
        btts_choices = find_market(odds, *kws)
        if btts_choices:
            break
    by_c = get_choice_odd(btts_choices, 'Yes')
    bn_c = get_choice_odd(btts_choices, 'No')
    by = odd_to_prob(by_c)
    bn = odd_to_prob(bn_c)
    if by and bn:
        by, bn = normalize2(by, bn)
        result['btts'] = {'yes': by, 'no': bn}
    else:
        result['btts'] = None

    # ---- Corners ----
    corner_choices = find_market(odds, 'corner')
    co_c = get_choice_odd(corner_choices, 'Over', '9.5') or get_choice_odd(corner_choices, 'Over 9.5')
    cu_c = get_choice_odd(corner_choices, 'Under', '9.5') or get_choice_odd(corner_choices, 'Under 9.5')
    co = odd_to_prob(co_c)
    cu = odd_to_prob(cu_c)
    if co and cu:
        co, cu = normalize2(co, cu)
        result['corners'] = {'over': co, 'under': cu, 'line': 9.5}
    else:
        result['corners'] = None

    # ---- Yellow Cards ----
    yellow_choices = []
    for kws in [('yellow card',), ('booking',), ('card',)]:
        yellow_choices = find_market(odds, *kws)
        if yellow_choices:
            break
    yo_c = get_choice_odd(yellow_choices, 'Over', '3.5') or get_choice_odd(yellow_choices, 'Over 3.5')
    yu_c = get_choice_odd(yellow_choices, 'Under', '3.5') or get_choice_odd(yellow_choices, 'Under 3.5')
    yo = odd_to_prob(yo_c)
    yu = odd_to_prob(yu_c)
    if yo and yu:
        yo, yu = normalize2(yo, yu)
        result['yellows'] = {'over': yo, 'under': yu, 'line': 3.5}
    else:
        result['yellows'] = None

    # ---- Statistical fallback for any missing markets ----
    missing = [k for k in ('1x2', 'goals', 'btts', 'corners', 'yellows') if result.get(k) is None]
    if missing:
        stat = calc_stat_predictions(event)
        for k in missing:
            result[k] = stat.get(k)

    return result


def has_high_confidence(preds, threshold=65.0):
    checks = []
    if preds.get('1x2'):
        checks += [preds['1x2'].get('home', 0), preds['1x2'].get('draw', 0), preds['1x2'].get('away', 0)]
    if preds.get('goals'):
        checks += [preds['goals'].get('over', 0), preds['goals'].get('under', 0)]
    if preds.get('btts'):
        checks += [preds['btts'].get('yes', 0), preds['btts'].get('no', 0)]
    if preds.get('corners'):
        checks += [preds['corners'].get('over', 0), preds['corners'].get('under', 0)]
    if preds.get('yellows'):
        checks += [preds['yellows'].get('over', 0), preds['yellows'].get('under', 0)]
    return any((v or 0) > threshold for v in checks)


def format_prob(val):
    if val is None:
        return 'N/D'
    return f"{val}%"


# ---------------------------------------------------------------------------
# Bot's own prediction logic
# ---------------------------------------------------------------------------
def get_team_form_icons(team_id, team_name=None, n=5):
    """Return emoji string for last n matches (🟢🟠🔴), oldest→newest.

    Tries FlashScore first (when team_name is provided), falls back to SofaScore.
    """
    # 1) FlashScore
    if team_name:
        fs_icons = _fs_team_form(team_name, n)
        if fs_icons:
            return "".join(fs_icons)

    # 2) SofaScore fallback
    data = sf_get(f"/team/{team_id}/events/last/0")
    events = [
        e for e in data.get('events', [])
        if e.get('status', {}).get('type') == 'finished'
    ][:n]

    team_id_int = int(team_id) if team_id is not None else None
    icons = []
    for e in events:
        home_team_id = e.get('homeTeam', {}).get('id')
        winner_code  = e.get('winnerCode')
        is_home = (home_team_id is not None and int(home_team_id) == team_id_int)

        if winner_code == 0:
            icons.append("🟠")
        elif winner_code == 1:
            icons.append("🟢" if is_home else "🔴")
        elif winner_code == 2:
            icons.append("🔴" if is_home else "🟢")
        else:
            hs  = int(e.get('homeScore', {}).get('current', 0) or 0)
            as_ = int(e.get('awayScore', {}).get('current', 0) or 0)
            scored, conceded = (hs, as_) if is_home else (as_, hs)
            icons.append("🟢" if scored > conceded else ("🟠" if scored == conceded else "🔴"))

    icons.reverse()
    return "".join(icons) if icons else "N/D"


def generar_pronostico_propio(home_name, away_name, preds):
    """Pick the single most probable outcome with its percentage."""
    candidatos = []

    p1x2 = preds.get('1x2') or {}
    home_p = p1x2.get('home', 0) or 0
    draw_p = p1x2.get('draw', 0) or 0
    away_p = p1x2.get('away', 0) or 0
    if home_p > 0:
        candidatos.append((home_p, f"victoria de <b>{h(home_name)}</b>"))
    if draw_p > 0:
        candidatos.append((draw_p, "empate"))
    if away_p > 0:
        candidatos.append((away_p, f"victoria de <b>{h(away_name)}</b>"))

    pgoals = preds.get('goals') or {}
    gl = pgoals.get('line', 2.5)
    go = pgoals.get('over', 0) or 0
    gu = pgoals.get('under', 0) or 0
    if go > 0:
        candidatos.append((go, f"+{gl} goles"))
    if gu > 0:
        candidatos.append((gu, f"-{gl} goles"))

    pbtts = preds.get('btts') or {}
    by = pbtts.get('yes', 0) or 0
    bn = pbtts.get('no', 0) or 0
    if by > 0:
        candidatos.append((by, "ambos equipos marcan"))
    if bn > 0:
        candidatos.append((bn, "al menos un equipo no marca"))

    pcorners = preds.get('corners') or {}
    cl = pcorners.get('line', 9.5)
    co = pcorners.get('over', 0) or 0
    cu = pcorners.get('under', 0) or 0
    if co > 0:
        candidatos.append((co, f"+{cl} córners"))
    if cu > 0:
        candidatos.append((cu, f"-{cl} córners"))

    if not candidatos:
        return "sin datos suficientes"

    candidatos.sort(key=lambda x: x[0], reverse=True)
    prob, texto = candidatos[0]
    return f"{texto} <i>({prob}%)</i>"


# ---------------------------------------------------------------------------
# Match formatter
# ---------------------------------------------------------------------------
def format_match(event, preds):
    home = event.get('homeTeam', {}).get('name', '?')
    away = event.get('awayTeam', {}).get('name', '?')
    ts = event.get('startTimestamp')
    if ts:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        hora_str = dt.strftime('%H:%M')
    else:
        hora_str = '--:--'

    prefix = "🔝 " if has_high_confidence(preds) else ""

    p1x2     = preds.get('1x2')
    pgoals   = preds.get('goals')
    pbtts    = preds.get('btts')
    pcorners = preds.get('corners')
    pyellows = preds.get('yellows')

    lines = []

    # Title: bold + underlined
    lines.append(f"{prefix}<b><u>{h(home)} vs {h(away)}</u></b>  ({hora_str} UTC)")

    # Each market: show only the more likely side
    if p1x2:
        picks = [
            (p1x2.get('home', 0), f"Local ({format_prob(p1x2.get('home'))})"),
            (p1x2.get('draw', 0), f"Empate ({format_prob(p1x2.get('draw'))})"),
            (p1x2.get('away', 0), f"Visitante ({format_prob(p1x2.get('away'))})"),
        ]
        best = max(picks, key=lambda x: x[0] or 0)
        lines.append(f"  📊 1X2: {best[1]}")
    else:
        lines.append("  📊 1X2: N/D")

    if pgoals:
        ln = pgoals.get('line', 2.5)
        go = pgoals.get('over', 0) or 0
        gu = pgoals.get('under', 0) or 0
        if go >= gu:
            lines.append(f"  ⚽ Goles: +{ln} ({format_prob(go)})")
        else:
            lines.append(f"  ⚽ Goles: -{ln} ({format_prob(gu)})")
    else:
        lines.append("  ⚽ Goles: N/D")

    if pbtts:
        by = pbtts.get('yes', 0) or 0
        bn = pbtts.get('no', 0) or 0
        if by >= bn:
            lines.append(f"  🎯 Ambos marcan: Sí ({format_prob(by)})")
        else:
            lines.append(f"  🎯 Ambos marcan: No ({format_prob(bn)})")
    else:
        lines.append("  🎯 Ambos marcan: N/D")

    if pcorners:
        cl = pcorners.get('line', 9.5)
        co = pcorners.get('over', 0) or 0
        cu = pcorners.get('under', 0) or 0
        if co >= cu:
            lines.append(f"  🚩 Córners: +{cl} ({format_prob(co)})")
        else:
            lines.append(f"  🚩 Córners: -{cl} ({format_prob(cu)})")
    else:
        lines.append("  🚩 Córners: N/D")

    if pyellows:
        yl = pyellows.get('line', 3.5)
        yo = pyellows.get('over', 0) or 0
        yu = pyellows.get('under', 0) or 0
        if yo >= yu:
            lines.append(f"  🟨 Amarillas: +{yl} ({format_prob(yo)})")
        else:
            lines.append(f"  🟨 Amarillas: -{yl} ({format_prob(yu)})")
    else:
        lines.append("  🟨 Amarillas: N/D")

    # Bot's own pick
    pronostico = generar_pronostico_propio(home, away, preds)
    lines.append(f"  🤖 <b>Mi pronóstico:</b> {pronostico}")

    # Last 5 form for each team (FlashScore → SofaScore fallback)
    home_id = event.get('homeTeam', {}).get('id')
    away_id = event.get('awayTeam', {}).get('id')
    if home_id and away_id:
        home_form = get_team_form_icons(home_id, team_name=home)
        away_form = get_team_form_icons(away_id, team_name=away)
        lines.append(f"  🏠 {h(home)}: {home_form}")
        lines.append(f"  ✈️ {h(away)}: {away_form}")

    # Occasional star player shot tip
    tiro = get_tiro_jugador(home, away)
    if tiro:
        lines.append(f"  {tiro}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Result match formatter (for /resultados)
# ---------------------------------------------------------------------------
def format_result_match(event):
    home = event.get('homeTeam', {}).get('name', '?')
    away = event.get('awayTeam', {}).get('name', '?')

    home_score = event.get('homeScore', {}).get('current', 0) or 0
    away_score = event.get('awayScore', {}).get('current', 0) or 0
    total_goals = home_score + away_score
    btts = home_score > 0 and away_score > 0

    if home_score > away_score:
        result_1x2 = "1 (Local)"
    elif home_score == away_score:
        result_1x2 = "X (Empate)"
    else:
        result_1x2 = "2 (Visitante)"

    event_id = event['id']
    stats = get_event_statistics(event_id)

    hc, ac = get_stat_total(stats, 'corner')
    total_corners = (hc or 0) + (ac or 0) if hc is not None else None

    hy, ay = get_stat_total(stats, 'yellow card')
    total_yellows = (hy or 0) + (ay or 0) if hy is not None else None

    def ck(condition):
        return "✅" if condition else "❌"

    lines = [f"<b><u>{h(home)} vs {h(away)}</u></b>"]
    lines.append(f"  📋 Resultado final: <b>{home_score} - {away_score}</b>")
    lines.append(f"  📊 1X2: {result_1x2}")
    goal_label = "más" if total_goals > 2.5 else "menos"
    lines.append(f"  ✅ Goles: {total_goals} total ({goal_label} de 2.5)")
    lines.append(f"  {ck(btts)} Ambos marcan: {'Sí' if btts else 'No'}")

    if total_corners is not None:
        corner_label = "más" if total_corners > 9.5 else "menos"
        lines.append(f"  ✅ Córners: {total_corners} total ({corner_label} de 9.5)")
    else:
        lines.append("  ❔ Córners: N/D")

    if total_yellows is not None:
        yellow_label = "más" if total_yellows > 3.5 else "menos"
        lines.append(f"  ✅ Amarillas: {total_yellows} total ({yellow_label} de 3.5)")
    else:
        lines.append("  ❔ Amarillas: N/D")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Bot handlers
# ---------------------------------------------------------------------------

def menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⚽ Pronósticos de hoy",      callback_data="menu_partidos_hoy"),
        types.InlineKeyboardButton("📊 Resultados de ayer",      callback_data="menu_resultados"),
        types.InlineKeyboardButton("❓ Ayuda",                   callback_data="menu_ayuda"),
    )
    return markup


@bot.message_handler(commands=['start'])
def cmd_start(message):
    texto = (
        "¡Bienvenido al bot de pronósticos de fútbol! ⚽\n\n"
        "Elige una opción del menú o usa los botones de abajo.\n\n"
        "<b>Leyenda:</b>\n"
        "🔝 = probabilidad &gt;65% en algún mercado\n"
        "🤖 = mi apuesta más probable"
    )
    bot.send_message(message.chat.id, texto, parse_mode="HTML", reply_markup=menu_markup())


@bot.message_handler(commands=['menu'])
def cmd_menu(message):
    bot.send_message(
        message.chat.id,
        "📋 <b>Menú principal</b>\nElige lo que quieres ver:",
        parse_mode="HTML",
        reply_markup=menu_markup()
    )


@bot.message_handler(commands=['help'])
def cmd_help(message):
    texto = (
        "📖 <b>Ayuda — Bot de Pronósticos</b>\n\n"
        "<b>Comandos disponibles:</b>\n"
        "/start — Bienvenida y menú principal\n"
        "/menu — Abrir el menú de opciones\n"
        "/partidos_hoy — Pronósticos por liga\n"
        "/help — Esta pantalla de ayuda\n\n"
        "<b>Leyenda de los pronósticos:</b>\n"
        "📊 1X2 — Resultado final (local/empate/visitante)\n"
        "⚽ Goles — Más o menos de 2.5 goles\n"
        "🎯 Ambos marcan — Los dos equipos anotan\n"
        "🚩 Córners — Más o menos de 9.5 saques de esquina\n"
        "🟨 Amarillas — Más o menos de 3.5 tarjetas\n"
        "🤖 Mi pronóstico — La apuesta que veo más probable\n"
        "🎯 Jugador destacado — Tip de tiro a puerta (cuando aplica)\n\n"
        "🔝 aparece cuando alguna probabilidad supera el 65%"
    )
    bot.send_message(message.chat.id, texto, parse_mode="HTML", reply_markup=menu_markup())


@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def callback_menu(call):
    bot.answer_callback_query(call.id)
    if call.data == "menu_partidos_hoy":
        cmd_partidos_hoy_chat(call.message.chat.id)
    elif call.data == "menu_resultados":
        cmd_resultados_chat(call.message.chat.id)
    elif call.data == "menu_ayuda":
        texto = (
            "📖 <b>Ayuda — Bot de Pronósticos</b>\n\n"
            "/menu — Abrir menú\n"
            "/partidos_hoy — Pronósticos por liga\n"
            "/resultados — Resultados de ayer con verificación\n\n"
            "🔝 = probabilidad &gt;65%\n"
            "🤖 = mi apuesta más probable\n"
            "✅ = estadística que se cumplió\n"
            "❌ = estadística que no se cumplió"
        )
        bot.send_message(call.message.chat.id, texto, parse_mode="HTML", reply_markup=menu_markup())


@bot.message_handler(commands=['resultados'])
def cmd_resultados(message):
    cmd_resultados_chat(message.chat.id)


def cmd_resultados_chat(chat_id):
    from datetime import timedelta
    ayer = str(date.today() - timedelta(days=1))
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(nombre, callback_data=f"res_{tid}")
        for nombre, tid in LIGAS
    ]
    markup.add(*buttons)
    bot.send_message(
        chat_id,
        f"📊 <b>Resultados de ayer ({ayer})</b>\nSelecciona una liga:",
        reply_markup=markup,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('res_'))
def callback_resultados_liga(call):
    tid = int(call.data.split('_')[1])
    liga_nombre = next((n for n, i in LIGAS if i == tid), "Liga")
    from datetime import timedelta
    ayer = str(date.today() - timedelta(days=1))

    bot.answer_callback_query(call.id, f"Cargando resultados de {liga_nombre}...")
    msg = bot.send_message(
        call.message.chat.id,
        f"🔍 Buscando resultados de <b>{h(liga_nombre)}</b> del {ayer}...",
        parse_mode="HTML"
    )

    events = get_yesterday_events_by_league(tid)

    if not events:
        bot.edit_message_text(
            f"❌ No hay partidos finalizados de <b>{h(liga_nombre)}</b> del {ayer}.",
            call.message.chat.id,
            msg.message_id,
            parse_mode="HTML"
        )
        return

    header = f"<b>📊 {h(liga_nombre)} — {ayer}</b>\n{'─' * 30}\n\n"
    current = header
    chunks = []

    for event in events:
        if event.get('status', {}).get('type') == 'canceled':
            continue
        block = format_result_match(event) + "\n"
        if len(current) + len(block) > 3800:
            chunks.append(current)
            current = block
        else:
            current += block

    if current.strip() and current != header:
        chunks.append(current)

    if not chunks:
        bot.edit_message_text(
            f"❌ No hay resultados disponibles de <b>{h(liga_nombre)}</b> del {ayer}.",
            call.message.chat.id,
            msg.message_id,
            parse_mode="HTML"
        )
        return

    first = True
    for chunk in chunks:
        if not chunk.strip():
            continue
        if first:
            bot.edit_message_text(chunk, call.message.chat.id, msg.message_id, parse_mode="HTML")
            first = False
        else:
            bot.send_message(call.message.chat.id, chunk, parse_mode="HTML")


@bot.message_handler(commands=['partidos_hoy'])
def cmd_partidos_hoy(message):
    cmd_partidos_hoy_chat(message.chat.id)


def cmd_partidos_hoy_chat(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(nombre, callback_data=f"liga_{tid}")
        for nombre, tid in LIGAS
    ]
    markup.add(*buttons)
    bot.send_message(
        chat_id,
        "⚽ <b>Selecciona una liga para ver los pronósticos de hoy:</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('liga_'))
def callback_liga(call):
    tid = int(call.data.split('_')[1])
    liga_nombre = next((n for n, i in LIGAS if i == tid), "Liga")

    bot.answer_callback_query(call.id, f"Cargando {liga_nombre}...")
    msg = bot.send_message(
        call.message.chat.id,
        f"🔍 Buscando partidos de <b>{h(liga_nombre)}</b> para hoy...",
        parse_mode="HTML"
    )

    events = get_events_by_league(tid)
    hoy = str(date.today())

    if not events:
        bot.edit_message_text(
            f"❌ No hay partidos de <b>{h(liga_nombre)}</b> programados para hoy ({hoy}).",
            call.message.chat.id,
            msg.message_id,
            parse_mode="HTML"
        )
        return

    header = f"<b>{h(liga_nombre)} — {hoy}</b>\n{'─' * 30}\n\n"
    current = header

    chunks = []
    for event in events:
        event_id = event['id']
        preds = get_predictions(event)
        block = format_match(event, preds) + "\n"

        if len(current) + len(block) > 3800:
            chunks.append(current)
            current = block
        else:
            current += block

    if current.strip() and current != header:
        chunks.append(current)

    first = True
    for chunk in chunks:
        if not chunk.strip():
            continue
        if first:
            bot.edit_message_text(
                chunk,
                call.message.chat.id,
                msg.message_id,
                parse_mode="HTML"
            )
            first = False
        else:
            bot.send_message(call.message.chat.id, chunk, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
def start_bot():
    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"Conectando a Telegram (intento {attempt})...")
            bot.infinity_polling(none_stop=True, timeout=30, long_polling_timeout=30)
            # If polling exits cleanly, restart anyway
            print("Polling finalizado. Reiniciando en 5s...")
            time.sleep(5)
        except telebot.apihelper.ApiTelegramException as e:
            if '409' in str(e):
                wait = min(attempt * 5, 60)
                print(f"Conflicto de sesión (409). Reintentando en {wait}s...")
                time.sleep(wait)
            else:
                print(f"Error de API: {e}. Reintentando en 10s...")
                time.sleep(10)
        except Exception as e:
            print(f"Error inesperado: {e}. Reiniciando en 5s...")
            time.sleep(5)

def registrar_comandos():
    comandos = [
        types.BotCommand("/start",         "🏠 Inicio y menú principal"),
        types.BotCommand("/menu",          "📋 Abrir menú de opciones"),
        types.BotCommand("/partidos_hoy",  "⚽ Pronósticos por liga"),
        types.BotCommand("/resultados",    "📊 Resultados de ayer con ✅/❌"),
        types.BotCommand("/help",          "❓ Ayuda y leyenda"),
    ]
    try:
        bot.set_my_commands(comandos)
        print("Menú de comandos registrado en Telegram.")
    except Exception as e:
        print(f"No se pudo registrar el menú: {e}")

if __name__ == '__main__':
    keep_alive()
    registrar_comandos()
    print("Bot iniciado. Esperando mensajes...")
    start_bot()
