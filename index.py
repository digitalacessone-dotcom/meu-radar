# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V104.0 - Geometria Perfeita & Full Logic
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

# Critérios para Alvos Militares/Raros
RARE_MODELS = ["C5", "C17", "B1", "B2", "B52", "F22", "F35", "F16", "F15", "F18", "A10", "U2", "P8", "K35R", "K46", "V22"]
RARE_CALLS = ["RCH", "PAT", "CNV", "GOTO", "NVY", "DOD", "FAF", "ASY", "CFC"]

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,visibility"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 45: "FOG", 61: "RAIN"}
        sky = mapping.get(curr['weather_code'], "CONDITIONS OK")
        return {"temp": f"{int(curr['temperature_2m'])}C", "sky": sky, "vis": f"{int(curr.get('visibility', 10000) / 1000)}KM"}
    except:
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
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
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": int(s.get('gs', 0) * 1.852), "kts": int(s.get('gs', 0)), "hd": int(s.get('track', 0)), "date": now_date, "time": now_time, "route": s.get('route', "--- ---"), "eta": round((d/(max(s.get('gs',1)*1.852,1)))*60), "vrate": int(s.get('baro_rate', 0)), "rare": is_rare, "type": tipo})
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
        
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 20px; z-index: 1000; transition: 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; transform: translateY(-20px); }
        input { flex: 1; padding: 15px; border-radius: 14px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 22px; border-radius: 14px; font-weight: 900; cursor: pointer; transition: 0.3s; }
        button:active { transform: scale(0.95); }
        
        .scene { width: 310px; height: 470px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .scene.flipped { transform: rotateY(180deg); }
        
        /* FIX: Borda Dourada Inteligente */
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 15px 40px rgba(0,0,0,0.4); border: none; transition: box-shadow 0.6s; }
        .face.back { transform: rotateY(180deg); background: #fcfcfc; padding: 25px; }
        
        .rare-active .face { box-shadow: 0 0 0 2px var(--gold), 0 20px 50px rgba(212, 175, 55, 0.2); }
        
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 25px; display: flex; flex-direction: column; justify-content: center; position: relative; transition: background 0.6s; }
        
        /* Perfuración Recortada com Borda */
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; z-index: 10; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:36px; height:36px; background:var(--bg); border-radius:50%; top:-18px; z-index: 20; transition: box-shadow 0.6s; }
        .perfor::before { left:-30px; } .perfor::after { right:-30px; }
        
        /* Borda interna da meia lua para fechar o contorno dourado */
        .rare-active .perfor::before { box-shadow: inset -2px 0 0 0 var(--gold); }
        .rare-active .perfor::after { box-shadow: inset 2px 0 0 0 var(--gold); }

        .main { flex: 1; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
        .flap { font-family: monospace; font-size: 19px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 15px; height: 23px; background: #f2f2f2; border-radius: 3px; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #ddd; }
        
        .rare-seal { 
            position: absolute; bottom: 35px; right: 35px; width: 80px; height: 80px;
            background: radial-gradient(circle, #fcf6ba 0%, #bf953f 100%);
            border-radius: 50%; opacity: 0; transform: scale(0.3) rotate(-30deg);
            transition: all 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: rgba(0,0,0,0.6); font-weight: 900; font-size: 9px; text-align: center;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.3);
        }
        .rare-active .rare-seal { opacity: 1; transform: scale(1) rotate(15deg); }

        .ticker { width: 320px; height: 40px; background: #000; border-radius: 10px; margin-top: 25px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 12px; border: 1px solid #222; overflow: hidden; }
        .sq { width: 11px; height: 11px; border: 1.5px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.3); border-radius: 2px; transition: 0.4s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 15px var(--gold); }

        @media (orientation: landscape) { 
            .scene { width: 580px; height: 280px; } 
            .face { flex-direction: row !important; } 
            .stub { width: 30% !important; height: 100% !important; } 
            .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } 
            .main { width: 70% !important; } .ticker { width: 580px; } 
            .perfor::before, .perfor::after { left: -18px; } .perfor::before { top: -30px; } .perfor::after { bottom: -30px; top: auto; }
            .rare-active .perfor::before { box-shadow: inset 0 -2px 0 0 var(--gold); }
            .rare-active .perfor::after { box-shadow: inset 0 2px 0 0 var(--gold); }
        }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER LOCATION (OR 'TEST')">
        <button onclick="startSearch()">SCAN</button>
    </div>

    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; font-weight:900; opacity:0.7; letter-spacing:1px;">RADAR SIGNAL</div>
                <div style="font-size:11px; font-weight:900; margin: 8px 0;" id="airl">WAITING...</div>
                <div style="font-size:72px; font-weight:900; letter-spacing:-6px;">19A</div>
                <div style="display:flex; gap:6px; margin-top:8px;">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 2px solid #333; padding: 5px 15px; border-radius: 6px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-top:20px;">
                    <div><span style="font-size: 8px; font-weight: 900; color: #aaa;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span style="font-size: 8px; font-weight: 900; color: #aaa;">DISTANCE</span><div id="f-dist" class="flap" style="color:#555"></div></div>
                    <div><span style="font-size: 8px; font-weight: 900; color: #aaa;">FLIGHT IDENT</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 8px; font-weight: 900; color: #aaa;">ROUTE (EST)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:20px;">
                    <div id="arr" style="font-size:52px; transition:2s cubic-bezier(0.19, 1, 0.22, 1); filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">✈</div>
                    <div style="text-align:right; color:var(--blue-txt); font-weight:900;">
                        <div id="f-date" style="font-size:12px; letter-spacing:1px;">-- --- ----</div>
                        <div id="f-time" style="font-size:22px; line-height:1;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=SCAN" style="width:125px; height:35px; opacity:0.15; margin-top:10px;" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:2px dashed #eee; border-radius:15px; padding:25px; display:flex; flex-direction:column; position:relative; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 8px; font-weight: 900; color: #bbb;">ALTITUDE BARO</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="spd-label" style="font-size: 8px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div style="border: 4px double var(--blue-txt); color: var(--blue-txt); padding: 25px; border-radius: 14px; transform: rotate(-6deg); align-self: center; text-align: center; font-weight: 900; background: rgba(52,168,201,0.03);">
                    <div style="font-size:9px; opacity:0.8; letter-spacing:2px;">SECURITY CHECK</div>
                    <div id="b-date" style="font-size:14px; margin: 4px 0;">-- --- ----</div>
                    <div id="b-time" style="font-size:32px; line-height:1;">--.--</div>
                    <div style="font-size:8px; margin-top:8px;">V104 AUTHENTICATED</div>
                </div>
                <div class="rare-seal">
                    <span style="letter-spacing:3px;">RARE</span>
                    <span id="seal-type" style="font-size:16px; margin:3px 0;">TYPE</span>
                    <span style="font-size:6px;">OFFICIAL DETECTION</span>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">INITIALIZING RADAR SYSTEM...</div>

    <script>
        let pos = null, act = null, isTest = false, unitToggle = true;
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
                    if(c++ > 22) { clearInterval(it); span.innerText = char === ' ' ? '\u00A0' : char; }
                }, 30);
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
                    } else { scene.classList.remove('rare-active'); }
                    
                    document.getElementById('stb').style.background = f.color;
                    document.getElementById('airl').innerText = f.airline;
                    
                    if(!act || act.icao !== f.icao) {
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        applyFlap('f-icao', f.icao);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }
                    
                    applyFlap('f-dist', f.dist + " KM");
                    applyFlap('b-alt', f.alt + " FT");
                    
                    const spdVal = unitToggle ? f.spd + " KMH" : f.kts + " KTS";
                    document.getElementById('spd-label').innerText = unitToggle ? "GROUND SPEED" : "AIRSPEED KTS";
                    applyFlap('b-spd', spdVal);

                    document.getElementById('f-date').innerText = f.date;
                    document.getElementById('f-time').innerText = f.time;
                    document.getElementById('b-date').innerText = f.date;
                    document.getElementById('b-time').innerText = f.time;
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = f.dist <= (190-(i-1)*40) ? 'sq on' : 'sq';
                    
                    tickerMsg = [`V.RATE: ${f.vrate} FPM`, `TEMP: ${d.weather.temp}`, `SKY: ${d.weather.sky}`, `VISIBILITY: ${d.weather.vis}`];
                    act = f;
                }
            } catch(e) { console.error(e); }
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
        setInterval(() => { unitToggle = !unitToggle; }, 8000);
    </script>
</body>
</html>
