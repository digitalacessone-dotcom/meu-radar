# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V102.0 - Elegance & Stealth
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

# Critérios para o Selo Secreto
RARE_MODELS = ["C5", "C17", "B1", "B2", "B52", "F22", "F35", "F16", "F15", "F18", "A10", "U2", "P8", "K35R", "K46", "V22"]
RARE_CALLS = ["RCH", "PAT", "CNV", "GOTO", "NVY", "DOD", "FAF", "ASY", "CFC"]

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
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200"
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
            return jsonify({"flight": {"icao": "AE0802", "reg": "06-6161", "call": "RCH144", "airline": "US AIR FORCE", "color": "#1a1a1a", "dist": 15.2, "alt": 34000, "spd": 830, "hd": 240, "date": now_date, "time": now_time, "route": "RMS-DOV", "eta": 1, "kts": 450, "vrate": -1500, "rare": True, "type": "C17"}, "weather": w, "date": now_date, "time": now_time})
        
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
                        tipo = s.get('t', '').upper()
                        is_rare = tipo in RARE_MODELS or any(call.startswith(p) for p in RARE_CALLS)
                        airline, color = "PRIVATE", "#444"
                        if is_rare: airline, color = "MILITARY / GOV", "#222"
                        elif call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": spd_kmh, "kts": spd_kts, "hd": int(s.get('track', 0)), "date": now_date, "time": now_time, "route": s.get('route', "--- ---"), "eta": round((d/(spd_kmh or 1))*60), "vrate": int(s.get('baro_rate', 0)), "rare": is_rare, "type": tipo})
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #D4AF37; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 2000px; overflow: hidden; }
        
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 1000; transition: 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 14px; border-radius: 14px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 20px; border-radius: 14px; font-weight: 900; cursor: pointer; }
        
        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .scene.flipped { transform: rotateY(180deg); }
        
        /* Rare Effects */
        .scene.rare-active .face { border: 1.5px solid var(--gold); box-shadow: 0 0 30px rgba(212, 175, 55, 0.25), 0 20px 50px rgba(0,0,0,0.5); }
        
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); border: 1px solid rgba(0,0,0,0.05); }
        .face.back { transform: rotateY(180deg); background: #f8f8f8; padding: 20px; }
        
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 25px; display: flex; flex-direction: column; justify-content: center; position: relative; transition: background 0.6s; }
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; z-index: 10; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:34px; height:34px; background:var(--bg); border-radius:50%; top:-17px; }
        .perfor::before { left:-28px; } .perfor::after { right:-28px; }
        
        .main { flex: 1; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        
        /* Secret Gold Seal */
        .rare-seal { 
            position: absolute; bottom: 30px; left: 30px; width: 70px; height: 70px;
            background: radial-gradient(circle, #fcf6ba 0%, #bf953f 100%);
            border-radius: 50%; opacity: 0; transform: scale(0.5) rotate(-20deg);
            transition: all 1s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: rgba(0,0,0,0.6); font-weight: 900; font-size: 8px; text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2), inset 0 0 10px rgba(0,0,0,0.1);
            border: 1px solid rgba(0,0,0,0.1); pointer-events: none;
        }
        .rare-active .rare-seal { opacity: 1; transform: scale(1) rotate(12deg); }
        .rare-seal::after { content: "CERTIFIED"; font-size: 6px; border-top: 1px solid rgba(0,0,0,0.2); margin-top: 2px; padding-top: 2px; }

        .ticker { width: 310px; height: 35px; background: #000; border-radius: 8px; margin-top: 20px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 1px; white-space: pre; border: 1px solid #222; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.2); border-radius: 2px; transition: 0.4s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 12px var(--gold); }

        @media (orientation: landscape) { 
            .scene { width: 560px; height: 270px; } 
            .face { flex-direction: row !important; } 
            .stub { width: 30% !important; height: 100% !important; } 
            .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } 
            .main { width: 70% !important; } .ticker { width: 560px; } 
            .perfor::before, .perfor::after { left: -17px; } .perfor::before { top: -28px; } .perfor::after { bottom: -28px; top: auto; }
            .rare-seal { bottom: 20px; left: auto; right: 20px; }
        }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER LOCATION">
        <button onclick="startSearch()">SCAN</button>
    </div>

    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900; opacity:0.6; letter-spacing:1px;">RADAR SIGNAL</div>
                <div style="font-size:10px; font-weight:900; margin: 6px 0;" id="airl">WAITING...</div>
                <div style="font-size:68px; font-weight:900; letter-spacing:-5px; margin-left:-3px;">19A</div>
                <div style="display:flex; gap:5px; margin-top:5px;">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 12px; border: 1.5px solid #333; padding: 4px 12px; border-radius: 5px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:15px;">
                    <div><span id="icao-l" style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-l" style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENT</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ROUTE (EST)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:48px; transition:1.8s cubic-bezier(0.165, 0.84, 0.44, 1);">✈</div>
                    <div style="text-align:right; color:var(--blue-txt); font-weight:900;">
                        <div id="f-date" style="font-size:11px;">-- --- ----</div>
                        <div id="f-time" style="font-size:18px; line-height:1;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=SCAN" style="width:115px; height:30px; opacity:0.12; margin-top:5px;" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1.5px dashed #ddd; border-radius:15px; padding:25px; display:flex; flex-direction:column; position:relative;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="spd-l" style="font-size: 7px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 18px; border-radius: 12px; transform: rotate(-8deg); align-self: center; margin-top: 35px; text-align: center; font-weight: 900; background: rgba(52, 168, 201, 0.05);">
                    <div style="font-size:8px; opacity:0.8;">SECURITY CLEARANCE</div>
                    <div id="b-date-l1" style="font-size:12px;">-- --- ----</div>
                    <div id="b-date-l2" style="font-size:26px; line-height:1;">--.--</div>
                    <div style="font-size:7px; margin-top:6px; letter-spacing:1px;">RADAR AUTHENTICATED V102</div>
                </div>

                <div class="rare-seal">
                    <span style="letter-spacing:2px;">RARE</span>
                    <span id="seal-type" style="font-size:14px; margin:2px 0;">TYPE</span>
                    <span style="font-size:5px;">AIRCRAFT FIND</span>
                </div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">INITIALIZING RADAR...</div>

    <script>
        let pos = null, act = null, prevDist = null, isTest = false, toggle = true;
        let tickerMsg = [], tickerIdx = 0;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const target = text.toUpperCase().padEnd(isTicker ? 32 : 8, ' ');
            container.innerHTML = '';
            [...target].forEach(char => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let c = 0; const it = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random()*chars.length)];
                    if(c++ > 25) { clearInterval(it); span.innerText = char === ' ' ? '\u00A0' : char; }
                }, 35);
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                if(d.flight) {
                    const f = d.flight;
                    const scene = document.getElementById('card');
                    
                    if(f.rare) {
                        scene.classList.add('rare-active');
                        document.getElementById('seal-type').innerText = f.type || "MIL";
                    } else {
                        scene.classList.remove('rare-active');
                    }

                    document.getElementById('stb').style.background = f.color;
                    document.getElementById('airl').innerText = f.airline;
                    
                    if(!act || act.icao !== f.icao) {
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        applyFlap('f-icao', f.icao);
                    }
                    
                    applyFlap('f-dist', f.dist + " KM");
                    applyFlap('b-alt', f.alt + " FT");
                    applyFlap('b-spd', toggle ? f.spd + " KMH" : f.kts + " KTS");
                    document.getElementById('spd-l').innerText = toggle ? "GROUND SPEED" : "AIRSPEED KTS";

                    document.getElementById('f-date').innerText = f.date;
                    document.getElementById('f-time').innerText = f.time;
                    document.getElementById('b-date-l1').innerText = f.date;
                    document.getElementById('b-date-l2').innerText = f.time;
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = f.dist <= (190-(i-1)*40) ? 'sq on' : 'sq';
                    
                    let trend = prevDist && f.dist < prevDist ? "CLOSING IN" : "STABLE";
                    tickerMsg = [`V.RATE: ${f.vrate} FPM`, trend, `TEMP: ${d.weather.temp}`, d.weather.sky];
                    prevDist = f.dist; act = f;
                } else {
                    tickerMsg = ["SCANNING HORIZON...", "NO SIGNAL"];
                }
            } catch(e) {}
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:0, lon:0}; hideUI(); }
            else { fetch("https://nominatim.openstreetmap.org/search?format=json&q="+v).then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:d[0].lat, lon:d[0].lon}; hideUI(); } }); }
        }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`); }
        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 15000); }
        
        setInterval(() => { if(tickerMsg.length) { applyFlap('tk', tickerMsg[tickerIdx], true); tickerIdx = (tickerIdx+1)%tickerMsg.length; }}, 6000);
        setInterval(() => { toggle = !toggle; }, 12000);
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
