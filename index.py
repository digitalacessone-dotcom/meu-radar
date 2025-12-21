# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V102 - Stability & Ripped Effect
RADIUS_KM = 200 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        resp = requests.get(url, timeout=3).json()
        temp = int(resp['current']['temperature_2m'])
        return {"temp": f"{temp}C", "sky": "OK"}
    except:
        return {"temp": "--C", "sky": "OFFLINE"}

def fetch_aircrafts(lat, lon):
    url = f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        return r.json().get('aircraft', []) if r.status_code == 200 else []
    except: return []

@app.route('/api/radar')
def radar():
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        test = request.args.get('test', 'false').lower() == 'true'
        now = get_time_local()
        
        if test:
            return jsonify({"flight": {"icao": "E4953E", "reg": "PT-MDS", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 8.4, "alt": 35000, "spd": 850, "hd": 120, "date": now.strftime("%d %b %Y").upper(), "time": now.strftime("%H.%M"), "route": "GIG-MIA"}, "weather": {"temp": "25C", "sky": "CLEAR"}})
        
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
                        airline, color = ("LATAM", "#E6004C") if call.startswith(("TAM", "JJ", "LA")) else ("GOL", "#FF6700") if call.startswith(("GLO", "G3")) else ("AZUL", "#004590") if call.startswith(("AZU", "AD")) else ("PRIVATE", "#444")
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": int(s.get('gs', 0) * 1.852), "hd": int(s.get('track', 0)), "date": now.strftime("%d %b %Y").upper(), "time": now.strftime("%H.%M"), "route": s.get('route', "--- ---")})
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "weather": get_weather(lat, lon)})
    except: return jsonify({"flight": None})

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --blue: #34a8c9; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; overflow: hidden; }
        
        #ui { margin-bottom: 15px; display: flex; gap: 8px; z-index: 100; transition: 0.5s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { padding: 12px; border-radius: 10px; border: none; background: #1a1d21; color: #fff; font-size: 14px; outline: none; }
        button { padding: 12px 20px; border-radius: 10px; border: none; font-weight: bold; cursor: pointer; background: #fff; }

        .container { width: 320px; height: 480px; position: relative; perspective: 1000px; }
        .card { width: 100%; height: 100%; position: relative; transition: transform 0.8s; transform-style: preserve-3d; }
        .flipped { transform: rotateY(180deg); }

        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; flex-direction: column; }
        .front { display: flex; flex-direction: column; gap: 0; }
        
        /* Partes do Ticket */
        .stub, .main { width: 100%; background: #fff; transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
        .stub { height: 30%; border-radius: 20px 20px 0 0; background: #444; color: #fff; padding: 20px; box-sizing: border-box; }
        .main { height: 70%; border-radius: 0 0 20px 20px; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; border-top: 2px dashed #eee; }

        /* Estado Ripped (Dist < 10km) */
        .ripped .stub { 
            transform: translateY(-15px) rotate(-1deg);
            clip-path: polygon(0% 0%, 100% 0%, 100% 90%, 95% 100%, 90% 90%, 85% 100%, 80% 90%, 75% 100%, 70% 90%, 65% 100%, 60% 90%, 55% 100%, 50% 90%, 45% 100%, 40% 90%, 35% 100%, 30% 90%, 25% 100%, 20% 90%, 15% 100%, 10% 90%, 5% 100%, 0% 90%);
        }
        .ripped .main { 
            transform: translateY(15px) rotate(1deg);
            clip-path: polygon(0% 10%, 5% 0%, 10% 10%, 15% 0%, 20% 10%, 25% 0%, 30% 10%, 35% 0%, 40% 10%, 45% 0%, 50% 10%, 55% 0%, 60% 10%, 65% 0%, 70% 10%, 75% 0%, 80% 10%, 85% 0%, 90% 10%, 95% 0%, 100% 10%, 100% 100%, 0% 100%);
        }

        .flap { font-family: monospace; font-size: 18px; font-weight: 900; display: flex; gap: 1px; color: #000; margin-bottom: 5px; }
        .char { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; min-width: 14px; text-align: center; }
        .sq { width: 10px; height: 10px; border: 1px solid rgba(255,255,255,0.3); display: inline-block; margin-right: 4px; border-radius: 2px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
        .ticker { margin-top: 20px; color: var(--gold); font-family: monospace; font-size: 11px; background: #000; padding: 10px; border-radius: 8px; width: 320px; text-align: center; letter-spacing: 1px; }
        .back { background: #f9f9f9; border-radius: 20px; transform: rotateY(180deg); padding: 20px; box-sizing: border-box; border: 1px solid #ddd; }
    </style>
</head>
<body onclick="handleCardClick(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER CITY">
        <button onclick="start()">CHECK-IN</button>
    </div>

    <div class="container">
        <div class="card" id="card">
            <div class="face front" id="t-front">
                <div class="stub" id="stb">
                    <div style="font-size:8px; opacity:0.6; font-weight:bold;">RADAR SCANNING</div>
                    <div id="airl" style="font-size:11px; font-weight:900; margin: 5px 0;">READY FOR SCAN</div>
                    <div style="font-size:60px; font-weight:900; letter-spacing:-3px;">19A</div>
                    <div id="dots">
                        <div class="sq"></div><div class="sq"></div><div class="sq"></div><div class="sq"></div><div class="sq"></div>
                    </div>
                </div>
                <div class="main">
                    <div style="border: 1.5px solid #000; padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: 900; width: fit-content;">BOARDING PASS</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 10px;">
                        <div><small style="font-size:7px; color:#aaa; font-weight:bold;">AIRCRAFT ICAO</small><div id="f-icao" class="flap"></div></div>
                        <div><small style="font-size:7px; color:#aaa; font-weight:bold;">DISTANCE</small><div id="f-dist" class="flap"></div></div>
                        <div><small style="font-size:7px; color:#aaa; font-weight:bold;">CALLSIGN</small><div id="f-call" class="flap"></div></div>
                        <div><small style="font-size:7px; color:#aaa; font-weight:bold;">ROUTE</small><div id="f-route" class="flap"></div></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div id="arr" style="font-size: 50px; transition: 1s;">✈</div>
                        <div style="text-align: right; color: var(--blue);">
                            <div id="f-date" style="font-size: 11px; font-weight: 900;">-- --- ----</div>
                            <div id="f-time" style="font-size: 22px; font-weight: 900;">--.--</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="face back">
                <div style="height:100%; border:2px dashed #ccc; border-radius:15px; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <div style="border:3px double var(--blue); color:var(--blue); padding:15px; transform:rotate(-15deg); font-weight:900; text-align:center;">
                        SECURITY CHECKED<br><small>V102 STABLE</small>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">WAITING FOR LOCATION...</div>

    <script>
        let pos = null, act = null, isTest = false;

        function applyFlap(id, text) {
            const el = document.getElementById(id);
            if(!el) return;
            const target = text.toUpperCase().padEnd(6, ' ').substring(0,6);
            el.innerHTML = '';
            [...target].forEach(c => {
                const s = document.createElement('span'); s.className = 'char';
                s.innerText = '-'; el.appendChild(s);
                setTimeout(() => { s.innerText = c === ' ' ? '\\u00A0' : c; }, 100 + Math.random() * 400);
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                const front = document.getElementById('t-front');

                if(d.flight) {
                    const f = d.flight;
                    // Lógica de Separação Física
                    if(f.dist < 10) front.classList.add('ripped');
                    else front.classList.remove('ripped');

                    if(!act || act.icao !== f.icao) {
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-icao', f.icao); applyFlap('f-call', f.call);
                        applyFlap('f-dist', f.dist + 'K'); applyFlap('f-route', f.route);
                    }
                    document.getElementById('f-date').innerText = f.date;
                    document.getElementById('f-time').innerText = f.time;
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    
                    const dots = document.getElementById('dots').children;
                    for(let i=0; i<5; i++) dots[i].className = f.dist <= (200-(i*40)) ? 'sq on' : 'sq';
                    
                    document.getElementById('tk').innerText = `LIVE: ${f.call} | ALT: ${f.alt}FT | SPD: ${f.spd}KMH`;
                    act = f;
                } else {
                    front.classList.remove('ripped');
                    document.getElementById('tk').innerText = `NO TRAFFIC NEARBY | TEMP: ${d.weather.temp}`;
                    act = null;
                }
            } catch(e) { console.error(e); }
        }

        function start() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-23, lon:-46}; finishInit(); }
            else {
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`)
                .then(r => r.json()).then(d => { if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; finishInit(); }});
            }
        }

        function handleCardClick(e) {
            if(!e.target.closest('#ui')) document.getElementById('card').classList.toggle('flipped');
        }

        function finishInit() {
            document.getElementById('ui').classList.add('hide');
            update(); setInterval(update, 15000);
        }

        navigator.geolocation.getCurrentPosition(p => { 
            pos = {lat:p.coords.latitude, lon:p.coords.longitude}; finishInit();
        }, () => {}, {timeout: 5000});
    </script>
</body>
</html>
