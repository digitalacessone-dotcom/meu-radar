# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V88 - ETA Dynamic Logic
RADIUS_KM = 200 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 45: "FOG", 51: "LIGHT DRIZZLE", 61: "RAIN", 80: "SHOWERS"}
    return mapping.get(code, "CONDITIONS OK")

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,relative_humidity_2m"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        return {"temp": f"{int(curr['temperature_2m'])}C", "sky": get_weather_desc(curr['weather_code'])}
    except:
        return {"temp": "--C", "sky": "METAR ON"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/250"
    ]
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    random.shuffle(endpoints)
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200: return r.json().get('aircraft', [])
        except: continue
    return []

@app.route('/api/radar')
def radar():
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        test = request.args.get('test', 'false').lower() == 'true'
        local_now = get_time_local()
        now_date = local_now.strftime("%d %b %Y").upper()
        now_time = local_now.strftime("%H.%M")
        w = get_weather(lat, lon)
        
        if test:
            return jsonify({"flight": {"icao": "E4953E", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 10.5, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time, "route": "GIG-MIA"}, "weather": w})
        
        data = fetch_aircrafts(lat, lon)
        found = None
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip()
                        airline, color = "PRIVATE", "#444"
                        if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        route = s.get('route', "--- ---")
                        spd = int(s.get('gs', 0) * 1.852)
                        eta = round((d / spd) * 60) if spd > 50 else 0
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": spd, "hd": int(s.get('track', 0)), "date": now_date, "time": now_time, "route": route, "eta": eta})
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; transition: opacity 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }
        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s; }
        .scene.flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #f4f4f4; padding: 15px; }
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; }
        .dots-container { display: flex; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 0.95; }
        #bc { width: 110px; height: 35px; opacity: 0.15; filter: grayscale(1); cursor: pointer; }
        .ticker { width: 310px; height: 32px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 1px; white-space: pre; }
        @media (orientation: landscape) { .scene { width: 550px; height: 260px; } .face { flex-direction: row !important; } .stub { width: 30% !important; height: 100% !important; } .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } .main { width: 70% !important; } .ticker { width: 550px; } }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER LOCATION">
        <button onclick="startSearch()">CHECK-IN</button>
    </div>
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900; opacity:0.7;">RADAR SCANNING</div>
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">SEARCHING TRAFFIC...</div>
                <div style="font-size:65px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div class="dots-container" id="dots"><div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div></div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 3px 10px; border-radius: 4px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-label" style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div class="date-visual"><div id="f-line1">-- --- ----</div><div id="f-line2">--.--</div><img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)"></div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:20px; display:flex; flex-direction:column;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 10px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 20px; text-align: center; font-weight: 900;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V88</div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">AWAITING LOCALIZATION...</div>
    <script>
        let pos = null, act = null, isTest = false, weather = null, distToggle = true;
        let tickerMsg = [], tickerIdx = 0;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            const limit = isTicker ? 25 : 8;
            const target = text.toUpperCase().padEnd(limit, ' ');
            container.innerHTML = '';
            [...target].forEach((char) => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let count = 0, max = 20 + Math.floor(Math.random() * 50); 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { clearInterval(interval); span.innerHTML = (char === ' ') ? '&nbsp;' : char; }
                }, 50); 
            });
        }

        setInterval(() => {
            if(act) {
                distToggle = !distToggle;
                document.getElementById('dist-label').innerText = distToggle ? "DISTANCE" : "ESTIMATED CONTACT";
                const val = distToggle ? act.dist + " KM" : "ETA " + act.eta + "M";
                applyFlap('f-dist', val);
            }
        }, 5000);

        function updateTicker() { if (tickerMsg.length > 0) { applyFlap('tk', tickerMsg[tickerIdx], true); tickerIdx = (tickerIdx + 1) % tickerMsg.length; } }
        setInterval(updateTicker, 15000);

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                weather = d.weather;
                if(d.flight) {
                    const f = d.flight;
                    document.getElementById('f-line1').innerText = f.date;
                    document.getElementById('f-line2').innerText = f.time;
                    document.getElementById('b-date-line1').innerText = f.date;
                    document.getElementById('b-date-line2').innerText = f.time;
                    if(!act || act.icao !== f.icao) {
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-icao', f.icao); applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        document.getElementById('bc').style.opacity = "0.8";
                    }
                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    if(!act || act.spd !== f.spd) applyFlap('b-spd', f.spd + " KMH");
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).classList.toggle('on', f.dist <= (250 - i*40));
                    act = f;
                    tickerMsg = [`SQUAWKING: ${f.call}`, `ROUTE: ${f.route}`, `RANGE: ${f.dist} KM`, `ETA: ${f.eta} MIN`, `SKY: ${weather.sky}`];
                } else { tickerMsg = [`SEARCHING TRAFFIC...`, `ESTIMATED TEMP: ${weather.temp}`, `SKY: ${weather.sky}`]; }
            } catch(e) {}
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`).then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } }); }
        }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }
        function hideUI() { document.getElementById('ui').classList.add('hide'); setTimeout(() => { update(); setInterval(update, 15000); }, 800); }
        navigator.geolocation.getCurrentPosition(p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, () => { applyFlap('tk', 'ENTER LOCATION ABOVE', true); }, { timeout: 6000 });
    </script>
</body>
</html>
''')
