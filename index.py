# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta
from functools import lru_cache

app = Flask(__name__)

# Configurações V106.2 - ANAC 2025 INTEGRATED
RADIUS_KM = 190 
DEFAULT_LAT = 37.24804
DEFAULT_LON = -115.800155

# LISTA DE MILITARES SOLICITADA
MIL_RARE = [
    'F14', 'F15', 'F16', 'F18', 'F22', 'F35', 'FA18', 'F4', 'F5', 'F117', 'A10', 'AV8B',
    'B1', 'B2', 'B52', 'C130', 'C17', 'C5', 'C160', 'A400', 'CN35', 'C295', 'C390', 'C212',
    'KC10', 'KC135', 'A332', 'K35R', 'KC76', 'P3', 'P8', 'E3', 'E8', 'E2', 'C2', 'RC135',
    'SU24', 'SU25', 'SU27', 'SU30', 'SU33', 'SU34', 'SU35', 'SU57', 'MIG21', 'MIG23', 'MIG25', 
    'MIG29', 'MIG31', 'MIG35', 'TU22', 'TU95', 'TU142', 'TU160', 'IL18', 'IL38', 'IL62', 'IL76', 
    'IL78', 'IL82', 'IL96', 'AN12', 'AN22', 'AN24', 'AN24', 'AN26', 'AN30', 'AN32', 'AN72', 'AN124', 'AN225',
    'J10', 'J11', 'J15', 'J16', 'J20', 'H6', 'KJ200', 'KJ500', 'KJ2000', 'Y8', 'Y9', 'Y20',
    'EUFI', 'RAFA', 'GRIP', 'TOR', 'HAWK', 'T38', 'M346', 'L39', 'K8', 'EMB3', 'AT27', 'C95', 
    'C97', 'C98', 'U27', 'R99', 'E99', 'P95', 'KC390', 'AMX', 'A1', 'A29'
]

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 45: "FOG", 51: "LIGHT DRIZZLE", 61: "RAIN", 80: "SHOWERS"}
    return mapping.get(code, "CONDITIONS OK")

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,visibility"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        vis_km = int(curr.get('visibility', 10000) / 1000)
        return {"temp": f"{int(curr['temperature_2m'])}C", "sky": get_weather_desc(curr['weather_code']), "vis": f"{vis_km}KM"}
    except:
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://api.adsb.one/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    all_aircraft = []
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                data = r.json().get('aircraft', [])
                if data: all_aircraft.extend(data)
        except: continue
    unique_data = {a['hex']: a for a in all_aircraft if 'hex' in a}.values()
    return list(unique_data)
    
@lru_cache(maxsize=128)
def fetch_route(callsign):
    if not callsign or callsign == "N/A": return "--- ---"
    try:
        # API mais robusta que integra dados do ADSB-Exchange
        url = f"https://api.adsb.lol/v2/callsign/{callsign.strip().upper()}"
        r = requests.get(url, timeout=4).json()
        if r.get('aircraft') and len(r['aircraft']) > 0:
            ac = r['aircraft'][0]
            # Tenta pegar a rota; se não tiver, pelo menos limpa o callsign
            rt = ac.get('route')
            if rt: return rt.replace('-', ' ').upper()
        return "EN ROUTE"
    except:
        return "EN ROUTE"

@app.route('/api/radar')
def radar():
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        current_icao = request.args.get('current_icao', None)
        test = request.args.get('test', 'false').lower() == 'true'
        local_now = get_time_local()
        now_date = local_now.strftime("%d %b %Y").upper()
        now_time = local_now.strftime("%H.%M")
        w = get_weather(lat, lon)
        
        if test:
            f = {"icao": "ABC123", "reg": "61-7972", "call": "BLACKBIRD", "airline": "SR-71 RARE", "color": "#000", "is_rare": True, "dist": 15.2, "alt": 80000, "spd": 3200, "hd": 350, "date": now_date, "time": now_time, "route": "BEALE-EDW", "eta": 2, "kts": 1800, "vrate": 0, "lat": lat + 0.1, "lon": lon + 0.1}
            return jsonify({"flight": f, "weather": w, "date": now_date, "time": now_time})
        
        data = fetch_aircrafts(lat, lon)
        found = None
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip().upper()
                        reg = (s.get('r') or 'N/A').upper()
                        r_info = s.get('route') or fetch_route(call.strip().upper())
                        type_code = (s.get('t') or '').upper()
                        airline, color, is_rare = "PRIVATE", "#444", False
                        
                        if s.get('mil') or type_code in MIL_RARE:
                            airline, color, is_rare = "MILITARY", "#000", True
                        elif call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM BRASIL", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL AIRLINES", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL LINHAS", "#004590"
                        elif call.startswith(("PTB", "2Z")): airline, color = "VOEPASS", "#F9A825"
                        elif call.startswith("SID"): airline, color = "SIDERAL CARGO", "#FF0000"
                        elif call.startswith("MWM"): airline, color = "MODERN LOG", "#202020"
                        elif call.startswith("OWT"): airline, color = "TOTAL CARGO", "#005544"
                        elif call.startswith("ABV"): airline, color = "ABAETE AVIAÇÃO", "#003366"
                        elif call.startswith("ASL"): airline, color = "AEROSUL", "#00BFFF"
                        elif call.startswith("SUL"): airline, color = "ASTA LINHAS", "#ED1C24"
                        elif call.startswith("TTL"): airline, color = "TOTAL LINHAS", "#005544"
                        elif call.startswith("PAM"): airline, color = "MAP LINHAS", "#0072CE"
                        elif call.startswith("VXP"): airline, color = "AVION EXPRESS", "#701630"
                        elif call.startswith("OMI"): airline, color = "OMNI TÁXI AÉREO", "#003366"
                        elif call.startswith("DPF"): airline, color, is_rare = "POLÍCIA FEDERAL", "#000", True
                        elif call.startswith("BRS"): airline, color, is_rare = "FAB MILITARY", "#003366", True
                        elif call.startswith("RYR"): airline, color = "RYANAIR", "#003399"
                        elif call.startswith("EZY"): airline, color = "EASYJET", "#FF6600"
                        elif call.startswith("SWA"): airline, color = "SOUTHWEST AIR", "#FFBF00"
                        elif call.startswith(("EJA", "NJE")): airline, color, is_rare = "NETJETS", "#000", True
                        elif "MLBR" in call or "MELI" in call: airline, color, is_rare = "MERCADO LIVRE", "#FFE600", True
                        elif call.startswith("GTI"): airline, color = "ATLAS AIR", "#003366"
                        elif call.startswith("CLX"): airline, color = "CARGOLUX", "#ED1C24"
                        elif call.startswith("ACA"): airline, color = "AIR CANADA", "#FF0000"
                        elif call.startswith("QTR"): airline, color = "QATAR AIRWAYS", "#5A0225"
                        elif call.startswith("SIA"): airline, color = "SINGAPORE AIR", "#11264B"
                        elif call.startswith("CPA"): airline, color = "CATHAY PACIFIC", "#00656B"
                        elif call.startswith("UAE"): airline, color = "EMIRATES", "#FF0000"
                        elif call.startswith("ANA"): airline, color = "ANA NIPPON", "#003192"
                        elif call.startswith("THY"): airline, color = "TURKISH AIR", "#C8102E"
                        elif call.startswith("KAL"): airline, color = "KOREAN AIR", "#003399"
                        elif call.startswith("AFR"): airline, color = "AIR FRANCE", "#002395"
                        elif call.startswith("AAL"): airline, color = "AMERICAN AIR", "#12316E"
                        elif call.startswith("DAL"): airline, color = "DELTA LINES", "#E01933"
                        elif call.startswith("UAL"): airline, color = "UNITED AIR", "#1B3E93"
                        elif call.startswith("DLH"): airline, color = "LUFTHANSA", "#002F5B"
                        elif call.startswith("CSN"): airline, color = "CHINA SOUTHERN", "#007AC1"
                        elif call.startswith("CMP"): airline, color = "COPA AIRLINES", "#003366"
                        elif call.startswith("BAW"): airline, color = "BRITISH AIR", "#002366"
                        elif call.startswith("IBE"): airline, color = "IBERIA", "#D7192D"
                        elif call.startswith("KLM"): airline, color = "KLM ROYAL", "#00A1DE"
                        elif call.startswith("SWR"): airline, color = "SWISS INT", "#E30613"
                        elif call.startswith("ARG"): airline, color = "AEROLINEAS ARG", "#00AEEF"
                        elif call.startswith("AVA"): airline, color = "AVIANCA", "#E01F26"
                        elif call.startswith("TAP"): airline, color = "TAP PORTUGAL", "#2F8E44"
                        elif call.startswith("FDX"): airline, color = "FEDEX", "#4D148C"
                        elif call.startswith("UPS"): airline, color = "UPS CARGO", "#351C15"
                        elif call.startswith("VJT"): airline, color, is_rare = "VISTAJET", "#C0C0C0", True
                        elif call.startswith("LXJ"): airline, color, is_rare = "FLEXJET", "#A52A2A", True
                        elif call.startswith("BCS"): airline, color = "DHL CARGO", "#D40511"
                        elif call.startswith(("ETH", "ET")): airline, color = "ETHIOPIAN AIR", "#006738"
                        elif call.startswith(("MSR", "MS")): airline, color = "EGYPTAIR", "#002855"
                        elif call.startswith(("SAA", "SA")): airline, color = "SOUTH AFRICAN", "#F9BE00"
                        elif call.startswith(("RAM", "AT")): airline, color = "ROYAL AIR MAROC", "#C2102E"
                        elif call.startswith(("KQA", "KQ")): airline, color = "KENYA AIRWAYS", "#C1121F"
                        elif call.startswith(("DLA", "AH")): airline, color = "AIR ALGERIE", "#D21034"
                        elif call.startswith(("LAA", "LN")): airline, color = "LIBYAN AIRLINES", "#000000"
                        elif call.startswith(("TUI", "BY")): airline, color = "TUI AIRWAYS", "#2AD2FF"
                        elif call.startswith(("ETD", "EY")): airline, color = "ETIHAD AIRWAYS", "#AD944D"
                        elif call.startswith(("AXM", "AK")): airline, color = "AIRASIA", "#ED1C24"
                        elif call.startswith(("JSA", "3K")): airline, color = "JETSTAR AIR", "#FF5000"
                        elif call.startswith(("FDB", "FZ")): airline, color = "FLYDUBAI", "#003264"
                        elif call.startswith(("RYN", "RD")): airline, color = "ROYAL JORDANIAN", "#8B0D1E"
                        elif call.startswith(("AIC", "AI")): airline, color = "AIR INDIA", "#ED1C24"
                        elif call.startswith(("IGO", "6E")): airline, color = "INDIGO", "#0055A4"
                        elif call.startswith(("EVA", "BR")): airline, color = "EVA AIR", "#006233"
                        elif call.startswith(("CAL", "CI")): airline, color = "CHINA AIRLINES", "#532E91"
                        elif call.startswith(("CES", "MU")): airline, color = "CHINA EASTERN", "#013B82"
                        elif call.startswith(("CHH", "HU")): airline, color = "HAINAN AIR", "#FFD700"
                        elif call.startswith(("GIA", "GA")): airline, color = "GARUDA INDONESIA", "#004C64"
                        elif call.startswith(("MAS", "MH")): airline, color = "MALAYSIA AIR", "#002244"
                        elif call.startswith(("THA", "TG")): airline, color = "THAI AIRWAYS", "#4A2483"
                        elif call.startswith(("HVN", "VN")): airline, color = "VIETNAM AIRLINES", "#006782"
                        elif call.startswith(("PAL", "PR")): airline, color = "PHILIPPINE AIR", "#013281"
                        elif call.startswith(("EVA", "BR")): airline, color = "EVA AIR", "#006233"
                        elif call.startswith(("SIA", "SQ")): airline, color = "SINGAPORE AIR", "#FFB200"
                        elif call.startswith(("CCA", "CA")): airline, color = "AIR CHINA", "#E30613"
                        elif call.startswith(("VJC", "VJ")): airline, color = "VIETJET AIR", "#F9A825"
                        elif call.startswith(("ITY", "AZ")): airline, color = "ITA AIRWAYS", "#004B96"
                        elif call.startswith(("SAS", "SK")): airline, color = "SCANDINAVIAN", "#003399"
                        elif call.startswith(("LOT", "LO")): airline, color = "LOT POLISH", "#003366"
                        elif call.startswith(("FIN", "AY")): airline, color = "FINNAIR", "#00005C"
                        elif call.startswith(("NAX", "DY")): airline, color = "NORWEGIAN AIR", "#D92121"
                        elif call.startswith(("BEL", "SN")): airline, color = "BRUSSELS AIR", "#003399"
                        elif call.startswith(("SWR", "LX")): airline, color = "SWISS AIR", "#E30613"
                        elif call.startswith(("AUA", "OS")): airline, color = "AUSTRIAN AIR", "#E30613"
                        elif call.startswith(("WZZ", "W6")): airline, color = "WIZZ AIR", "#D0006F"
                        elif call.startswith(("PGT", "PC")): airline, color = "PEGASUS AIR", "#FFD700"
                        elif call.startswith(("AEE", "A3")): airline, color = "AEGEAN AIR", "#002E62"
                        elif call.startswith(("ICE", "FI")): airline, color = "ICELANDAIR", "#00205B"
                        elif call.startswith(("TRA", "HV")): airline, color = "TRANSAVIA", "#00D66C"
                        elif call.startswith(("AEA", "UX")): airline, color = "AIR EUROPA", "#0066FF"
                        elif call.startswith(("VLG", "VY")): airline, color = "VUELING", "#FFD700"
                        elif call.startswith(("JBU", "B6")): airline, color = "JETBLUE", "#00205B"
                        elif call.startswith(("NKS", "NK")): airline, color = "SPIRIT AIR", "#FFEC00"
                        elif call.startswith(("FFT", "F9")): airline, color = "FRONTIER AIR", "#006644"
                        elif call.startswith(("ASA", "AS")): airline, color = "ALASKA AIR", "#00426A"
                        elif call.startswith(("HAL", "HA")): airline, color = "HAWAIIAN AIR", "#93268F"
                        elif call.startswith(("AAY", "G4")): airline, color = "ALLEGIANT AIR", "#FBBA00"
                        elif call.startswith(("AMX", "AM")): airline, color = "AEROMEXICO", "#00235D"
                        elif call.startswith(("VOI", "Y4")): airline, color = "VOLARIS", "#000000"
                        elif call.startswith(("VIV", "VB")): airline, color = "VIVA AEROBUS", "#00A650"
                        elif call.startswith(("WJA", "WS")): airline, color = "WESTJET", "#003A5D"
                        elif call.startswith(("RPA", "YX")): airline, color = "REPUBLIC AIR", "#1D3263"
                        elif call.startswith(("SKW", "OO")): airline, color = "SKYWEST AIR", "#003366"
                        elif call.startswith(("PDT", "PT")): airline, color = "PIEDMONT AIR", "#C41230"
                        elif call.startswith(("ENY", "MQ")): airline, color = "ENVOY AIR", "#AD1124"
                        elif call.startswith(("QFA", "QF")): airline, color = "QANTAS", "#E3001B"
                        elif call.startswith(("ANZ", "NZ")): airline, color = "AIR NEW ZEALAND", "#000000"
                        elif call.startswith(("VOZ", "VA")): airline, color = "VIRGIN AUSTRALIA", "#E21737"
                        elif call.startswith(("JST", "JQ")): airline, color = "JETSTAR", "#FF5100"
                        elif call.startswith(("PAC", "PO")): airline, color = "POLAR CARGO", "#003366"
                        elif call.startswith(("CKS", "K4")): airline, color = "KALITTA AIR", "#ED1C24"
                        elif call.startswith(("AZG", "ZP")): airline, color = "SILK WAY WEST", "#001D41"
                        elif call.startswith(("BOX", "3S")): airline, color = "AEROLOGIC", "#FFD700"
                        elif call.startswith(("TAY", "3V")): airline, color = "ASL BELGIUM", "#FF6600"
                        elif call.startswith(("VDA", "VI")): airline, color, is_rare = "VOLGA-DNEPR", "#003399", True
                        elif call.startswith("XRO"): airline, color, is_rare = "JET FLYER", "#000", True
                        elif call.startswith("FYL"): airline, color, is_rare = "FLYING GROUP", "#8B0000", True
                        elif call.startswith("VMP"): airline, color, is_rare = "VAMP AIR", "#333", True
                        elif call.startswith("AXY"): airline, color, is_rare = "AIRX CHARTER", "#000", True
                        elif call.startswith("FYG"): airline, color, is_rare = "FLYING SERVICE", "#555", True
                        elif call.startswith(("SKU", "H2")): airline, color = "SKY AIRLINE", "#FF00FF"
                        elif call.startswith(("JAT", "JA")): airline, color = "JETSMART", "#003366"
                        elif call.startswith(("LPE", "LP")): airline, color = "LATAM PERU", "#E6004C"
                        elif call.startswith(("LNE", "XL")): airline, color = "LATAM ECUADOR", "#E6004C"
                        elif call.startswith(("LNC", "4C")): airline, color = "LATAM COLOMBIA", "#E6004C"
                        elif call.startswith(("LAN", "LA")): airline, color = "LATAM CHILE", "#E6004C"
                        elif call.startswith(("BOV", "OB")): airline, color = "BOLIVIANA AVIACION", "#003399"
                        elif call.startswith(("CUB", "CU")): airline, color = "CUBANA DE AVIACION", "#003399"
                        elif call.startswith(("BWY", "BW")): airline, color = "CARIBBEAN AIRLINES", "#00AEEF"
                        elif call.startswith(("GIA", "GA")): airline, color = "GARUDA INDONESIA", "#004C64"
                        elif call.startswith(("TAI", "TA")): airline, color = "AVIANCA EL SALVADOR", "#E01F26"
                        elif call.startswith(("LRC", "LR")): airline, color = "AVIANCA COSTA RICA", "#E01F26"
                        elif call.startswith(("GLG", "G3")): airline, color = "GOL (INTL)", "#FF6700"
                        elif call.startswith("CMX"): airline, color = "AEROMEXICO CONNECT", "#00235D"
                        elif call.startswith(("ELY", "LY")): airline, color = "EL AL ISRAEL", "#00205B"
                        elif call.startswith(("SVA", "SV")): airline, color = "SAUDIA AIR", "#133E3C"
                        elif call.startswith(("KAC", "KU")): airline, color = "KUWAIT AIRWAYS", "#004B91"
                        elif call.startswith(("KZR", "KC")): airline, color = "AIR ASTANA", "#988252"
                        elif call.startswith(("CFG", "DE")): airline, color = "CONDOR", "#FBC400"
                        elif call.startswith(("TUI", "TB")): airline, color = "TUI FLY BELGIUM", "#2AD2FF"
                        elif call.startswith("VRE"): airline, color, is_rare = "VOLARE AIR", "#000", True
                        elif call.startswith("GES"): airline, color, is_rare = "GESTAIR", "#222", True
                        elif call.startswith("LAV"): airline, color, is_rare = "ALBASTAR", "#E21E26"
                        elif call.startswith("SWT"): airline, color = "SWIFTAIR", "#004A99"
                        elif call.startswith("PWP"): airline, color = "PARANAIR", "#003366"
                        elif call.startswith("FBZ"): airline, color = "FLYBONDI", "#FFD700"
                        elif call.startswith("LDR"): airline, color, is_rare = "LIDER AVIAÇÃO", "#000", True
                        elif call.startswith("NCR"): airline, color = "NATIONAL AIR", "#003366"
                        elif call.startswith("ICV"): airline, color = "CARGOLUX ITALIA", "#ED1C24"
                        elif call.startswith("VIR"): airline, color = "VIRGIN ATLANTIC", "#C8102E"
                        elif call.startswith("AFL"): airline, color = "AEROFLOT", "#003399"
                        elif call.startswith("VUK"): airline, color = "VOLOTEA", "#FF4F00"
                        elif call.startswith("EXS"): airline, color = "JET2", "#ED1C24"
                        elif call.startswith("RZO"): airline, color = "SATA AZORES", "#004B91"
                        elif call.startswith("TPA"): airline, color = "AVIANCA CARGO", "#E01F26"
                        elif call.startswith("KRE"): airline, color, is_rare = "AEROSUCRE", "#FFD700", True
                        elif call.startswith("OAE"): airline, color, is_rare = "OMNI AIR INTL", "#1D2951", True
                        elif call.startswith("ICV"): airline, color = "CARGOLUX ITALIA", "#ED1C24"
                        elif call.startswith("BOS"): airline, color = "OPEN SKIES", "#003366"
                        elif call.startswith("RPB"): airline, color = "COPA COLOMBIA", "#003366"
                        elif call.startswith("PUE"): airline, color = "PLUS ULTRA", "#D7192D"
                        elif call.startswith("VCV"): airline, color, is_rare = "CONVIASA", "#003366", True
                        elif call.startswith("WTI"): airline, color = "WORLD TICKET", "#555"
                        elif "SANTA" in call or "HOHOHO" in call or type_code == "SLEI": 
                            airline, color, is_rare = "SANTA CLAUS", "#D42426", True
                        
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        eta = round((d / (spd_kmh or 1)) * 60)
                        r_info = s.get('route') or fetch_route(call.strip().upper())

                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(), 
                            "reg": s.get('r', 'N/A').upper(), 
                            "call": call, "airline": airline, 
                            "color": color, "is_rare": is_rare, 
                            "dist": round(d, 1), 
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), 
                            "spd": spd_kmh, "kts": spd_kts, 
                            "hd": int(s.get('track', 0)), 
                            "lat": slat, "lon": slon,
                            "date": now_date, "time": now_time, 
                            "route": r_info, "eta": eta, 
                            "vrate": int(s.get('baro_rate', 0))
                        })
            
            if proc:
                proc.sort(key=lambda x: x['dist'])
                new_closest = proc[0]
                if current_icao:
                    current_on_radar = next((x for x in proc if x['icao'] == current_icao), None)
                    if current_on_radar:
                        found = new_closest if new_closest['dist'] < (current_on_radar['dist'] - 5) else current_on_radar
                    else: found = new_closest
                else: found = new_closest

        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time})
    except: return jsonify({"flight": None})

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        
        #ui { width: 280px; display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; z-index: 1; transition: all 1.2s cubic-bezier(0.4, 0, 0.2, 1); }
        #ui.hide { opacity: 0; pointer-events: none; transform: translateY(150px) scale(0.9); }
        .ui-row { display: flex; gap: 6px; }
        
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; transition: all 0.3s ease; }
        input:focus { background: #252a30; box-shadow: 0 0 0 2px rgba(255,255,255,0.1); }
        
        button { background: #fff; border: none; padding: 10px 15px; border-radius: 12px; font-weight: 900; cursor: pointer; transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        button:active { transform: scale(0.95); }
        
        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s, width 0.5s ease, height 0.5s ease; z-index: 10; }
        .scene.flipped { transform: rotateY(180deg); }
        
        .face { 
            position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; 
            background: #fdfaf0;
            background-image: 
                linear-gradient(to right, rgba(0,0,0,0.03) 0%, transparent 10%, transparent 90%, rgba(0,0,0,0.03) 100%),
                url('https://www.transparenttextures.com/patterns/paper-fibers.png');
            display: flex; flex-direction: column; overflow: hidden; 
            box-shadow: 0 20px 50px rgba(0,0,0,0.5), inset 0 0 100px rgba(212, 186, 134, 0.1); 
        }

        .face.back { transform: rotateY(180deg); padding: 15px; }
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: 0.5s; position: relative; }
        .stub::before { content: ""; position: absolute; top:0; left:0; width:100%; height:100%; background: url('https://www.transparenttextures.com/patterns/paper-fibers.png'); opacity: 0.2; pointer-events: none; }
        .stub.rare-mode { background: #000 !important; color: var(--gold) !important; }
        
        .dots-container { display: flex; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; transition: 0.3s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
        
        .perfor { height: 2px; border-top: 5px dotted rgba(0,0,0,0.1); position: relative; z-index: 2; transition: none; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; transition: none; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }
        
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #1a1a1a; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: rgba(0,0,0,0.05); border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 0.95; text-align: right; }
        #bc { width: 110px; height: 35px; opacity: 0.3; filter: grayscale(1); cursor: pointer; margin-top: 5px; mix-blend-mode: multiply; }
        
        .ticker { width: 310px; height: 32px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 2px; white-space: pre; transition: width 0.5s ease; z-index: 10; }
        
        .metal-seal { position: absolute; bottom: 30px; right: 20px; width: 85px; height: 85px; border-radius: 50%; background: radial-gradient(circle, #f9e17d 0%, #d4af37 40%, #b8860b 100%); border: 2px solid #8a6d3b; box-shadow: 0 4px 10px rgba(0,0,0,0.3), inset 0 0 10px rgba(255,255,255,0.5); display: none; flex-direction: column; align-items: center; justify-content: center; transform: rotate(15deg); z-index: 10; border-style: double; border-width: 4px; }
        .metal-seal span { color: #5c4412; font-size: 8px; font-weight: 900; text-align: center; text-transform: uppercase; line-height: 1; padding: 2px; }
        
        #compass-btn { font-size: 9px; background: #222; color: #fff; margin-top: 5px; padding: 5px; opacity: 0.6; }

        @media (orientation: landscape) { 
            .scene { width: 550px; height: 260px; } 
            .face { flex-direction: row !important; } 
            .stub { width: 30% !important; height: 100% !important; } 
            .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted rgba(0,0,0,0.1) !important; border-top: none !important; margin: 0; } 
            .perfor::before { left: -15px; top: -25px; }
            .perfor::after { left: -15px; bottom: -25px; top: auto; }
            .main { width: 70% !important; } 
            .ticker { width: 550px; } 
        }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <div class="ui-row">
            <input type="text" id="in" placeholder="ENTER LOCATION">
            <button onclick="startSearch(event)">CHECK-IN</button>
        </div>
        <button id="compass-btn" onclick="initCompass()">ENABLE LIVE TRACKING SENSORS</button>
    </div>
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900; opacity:0.7;">RADAR SCANNING</div>
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">SEARCHING...</div>
                <div style="font-size:65px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div class="dots-container" id="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 3px 10px; border-radius: 4px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div><span id="icao-label" style="font-size: 7px; font-weight: 900; color: #888;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-label" style="font-size: 7px; font-weight: 900; color: #888;">DISTANCE</span><div id="f-dist" class="flap" style="color:#444"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #888;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #888;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition: transform 0.2s cubic-bezier(0.17, 0.67, 0.83, 0.67); filter: drop-shadow(0 2px 2px rgba(0,0,0,0.1));">✈</div>
                    <div class="date-visual">
                        <div id="f-line1">-- --- ----</div>
                        <div id="f-line2">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed rgba(0,0,0,0.15); border-radius:15px; padding:20px; display:flex; flex-direction:column; position:relative;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #888;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="spd-label" style="font-size: 7px; font-weight: 900; color: #888;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 15px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 30px; text-align: center; font-weight: 900; opacity: 0.8;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V106.2</div>
                </div>
                <div id="gold-seal" class="metal-seal">
                    <span>Rare</span>
                    <span style="font-size:10px;">Aircraft</span>
                    <span>Found</span>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">WAITING...</div>

    <script>
        // --- INÍCIO WAKE LOCK (TELA SEMPRE ATIVA iOS 26) ---
        let wakeLock = null;
        const requestWakeLock = async () => {
            try {
                if ('wakeLock' in navigator) {
                    wakeLock = await navigator.wakeLock.request('screen');
                }
            } catch (err) {}
        };
        document.addEventListener('visibilitychange', async () => {
            if (wakeLock !== null && document.visibilityState === 'visible') {
                await requestWakeLock();
            }
        });
        // --- FIM WAKE LOCK ---

        let pos = null, act = null, isTest = false;
        let toggleState = true, tickerMsg = [], tickerIdx = 0, audioCtx = null;
        let lastDist = null;
        let deviceHeading = 0;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function initCompass() {
            if (typeof DeviceOrientationEvent.requestPermission === 'function') {
                DeviceOrientationEvent.requestPermission()
                    .then(state => {
                        if (state === 'granted') {
                            window.addEventListener('deviceorientation', handleOrientation);
                            document.getElementById('compass-btn').style.display = 'none';
                        }
                    });
            } else {
                window.addEventListener('deviceorientation', handleOrientation);
                document.getElementById('compass-btn').style.display = 'none';
            }
        }

        function handleOrientation(e) {
            let heading = e.webkitCompassHeading || (360 - e.alpha);
            
            // CORREÇÃO PARA MODO DEITADO (LANDSCAPE)
            const isLandscape = window.innerWidth > window.innerHeight;
            if (isLandscape) {
                // Ajusta o heading em 90 graus para compensar a rotação do dispositivo
                heading = (heading + 90) % 360;
            }
            
            deviceHeading = heading;
            updatePlaneVisual();
        }

        function calculateBearing(lat1, lon1, lat2, lon2) {
            const l1 = lat1 * Math.PI / 180;
            const l2 = lat2 * Math.PI / 180;
            const dl = (lon2 - lon1) * Math.PI / 180;
            const y = Math.sin(dl) * Math.cos(l2);
            const x = Math.cos(l1) * Math.sin(l2) - Math.sin(l1) * Math.cos(l2) * Math.cos(dl);
            return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
        }

        function updatePlaneVisual() {
            if(!act || !pos) return;
            const planeElement = document.getElementById('arr');
            const bearingToPlane = calculateBearing(pos.lat, pos.lon, act.lat, act.lon);
            const finalRotation = (bearingToPlane - deviceHeading - 45);
            planeElement.style.transform = `rotate(${finalRotation}deg)`;
        }

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, audioCtx.currentTime); 
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.5);
            } catch(e) {}
        }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const targetText = text.toUpperCase();
            // INTELIGENTE: Se o texto for igual ao anterior, não faz nada (protege CPU)
            if (container.getAttribute('data-last') === targetText) return;
            container.setAttribute('data-last', targetText);
            const limit = isTicker ? 32 : 8;
            const target = text.toUpperCase().padEnd(limit, ' ');
            container.innerHTML = '';
            [...target].forEach((char) => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let count = 0;
                let max = 40 + Math.floor(Math.random() * 80); 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { 
                        clearInterval(interval); 
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char; 
                    }
                }, 20);
            });
        }

        function saveHistory(f) {
            if(isTest) return;
            if(!f.is_rare) return;
            let history = JSON.parse(localStorage.getItem('rare_flights') || '[]');
            if(!history.find(x => x.icao === f.icao)) {
                history.push({icao: f.icao, call: f.call, date: f.date, time: f.time});
                localStorage.setItem('rare_flights', JSON.stringify(history));
            }
        }

        setInterval(() => {
            if(act) {
                toggleState = !toggleState;
                document.getElementById('icao-label').innerText = toggleState ? "AIRCRAFT ICAO" : "REGISTRATION";
                applyFlap('f-icao', toggleState ? act.icao : act.reg);
                document.getElementById('dist-label').innerText = toggleState ? "DISTANCE" : "ESTIMATED CONTACT";
                applyFlap('f-dist', toggleState ? act.dist + " KM" : "ETA " + act.eta + "M");
                document.getElementById('spd-label').innerText = toggleState ? "GROUND SPEED" : "AIRSPEED INDICATOR";
                applyFlap('b-spd', toggleState ? act.spd + " KMH" : act.kts + " KTS");
            }
        }, 12000);

        function updateTicker() { 
            if (tickerMsg.length > 0) { 
                applyFlap('tk', tickerMsg[tickerIdx], true); 
                tickerIdx = (tickerIdx + 1) % tickerMsg.length; 
            } 
        }
        setInterval(updateTicker, 15000);

        async function update() {
            if(!pos) return;
            try {
                const current_icao = act ? act.icao : '';
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&current_icao=${current_icao}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                
                if(d.flight) {
                    const f = d.flight;
                    const stub = document.getElementById('stb');
                    const seal = document.getElementById('gold-seal');

                    let trend = "MAINTAINING";
                    if(lastDist !== null) {
                        if(f.dist < lastDist - 0.1) trend = "CLOSING IN";
                        else if(f.dist > lastDist + 0.1) trend = "MOVING AWAY";
                    }
                    lastDist = f.dist;

                    if(f.is_rare) {
                        stub.className = 'stub rare-mode';
                        seal.style.display = 'flex';
                        saveHistory(f);
                    } else {
                        stub.className = 'stub';
                        stub.style.background = f.color;
                        seal.style.display = 'none';
                    }

                    if(!act || act.icao !== f.icao) {
                        playPing();
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        
                        document.getElementById('f-line1').innerText = f.date;
                        document.getElementById('f-line2').innerText = f.time;
                        document.getElementById('b-date-line1').innerText = f.date;
                        document.getElementById('b-date-line2').innerText = f.time;
                    }

                    for(let i=1; i<=5; i++) {
                        const threshold = 190 - ((i-1) * 40);
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }
                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    
                    tickerMsg = ["CONTACT ESTABLISHED", trend, d.weather.temp + " " + d.weather.sky];
                    act = f;
                    updatePlaneVisual();
                } else if (act) {
                    tickerMsg = ["SIGNAL LOST / GHOST MODE ACTIVE", "SEARCHING TRAFFIC..."];
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                    document.getElementById('stb').className = 'stub';
                    document.getElementById('stb').style.background = 'var(--brand)';
                } else {
                    tickerMsg = ["SEARCHING TRAFFIC..."];
                }
            } catch(e) {}
        }

        function startSearch(e) {
            requestWakeLock(); // <--- ACRESCENTE ESTA LINHA
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const btn = e.target;
            const v = document.getElementById('in').value.toUpperCase();
            
            btn.style.transform = "scale(0.9)";
            setTimeout(() => btn.style.transform = "scale(1)", 150);

            tickerMsg = ["SEARCHING TRAFFIC..."];
            updateTicker();
            
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { 
                fetch("https://nominatim.openstreetmap.org/search?format=json&q="+v)
                .then(r=>r.json())
                .then(d=>{ 
                    if(d[0]) { 
                        pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; 
                        hideUI(); 
                    } 
                }); 
            }
        }
        
        function handleFlip(e) { 
            if(!e.target.closest('#ui') && !e.target.closest('#bc')) {
                document.getElementById('card').classList.toggle('flipped'); 
            }
        }
        
        function openMap(e) { 
            e.stopPropagation(); 
            if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); 
        }
        
        function hideUI() { 
            const ui = document.getElementById('ui');
            ui.classList.add('hide'); 
            setTimeout(() => {
                update(); 
                setInterval(update, 15000); 
            }, 800);
        }

        let wakeLock = null;
        async function requestWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    wakeLock = await navigator.wakeLock.request('screen');
                    console.log("Wake Lock Ativo");
                }
            } catch (err) { console.log("Erro WakeLock:", err); }
        }
        // Reativar se você sair da aba e voltar
        document.addEventListener('visibilitychange', async () => {
            if (wakeLock !== null && document.visibilityState === 'visible') {
                await requestWakeLock();

        // AUTO GPS INTEGRATION
        navigator.geolocation.getCurrentPosition(p => {
            pos = {lat: p.coords.latitude, lon: p.coords.longitude};
            hideUI();
            requestWakeLock(); // <--- ACRESCENTE ESTA LINHA
        }, e => console.log(e));

    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
