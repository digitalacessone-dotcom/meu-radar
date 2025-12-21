# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V94 - Enhanced UI & Contrast
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
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}/longitude={lon}&current=temperature_2m,weather_code"
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
    headers = {'User-Agent': 'Mozilla/5.0'}
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
            return jsonify({"flight": {"icao": "E4953E", "reg": "PT-MDS", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 9.5, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time, "route": "GIG-MIA", "eta": 1, "kts": 459}, "weather": w, "date": now_date, "time": now_time})
        
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
                        airline, color = "PRIVATE", "#2c3e50"
                        if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        eta = round((d / (spd_kmh or 1)) * 60)
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": spd_kmh, "kts": spd_kts, "hd": int(s.get('track', 0)), "date": now_date, "time": now_time, "route": s.get('route', "GIG-MIA"), "eta": eta})
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
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 2000px; overflow: hidden; }
        
        #ui { width: 300px; display: flex; gap: 6px; margin-bottom: 20px; z-index: 500; transition: 0.5s; }
        #ui.hide { opacity: 0; pointer-events: none; transform: translateY(-20px); }
        input { flex: 1; padding: 14px; border-radius: 12px; border: 1px solid #333; background: #1a1d21; color: #fff; font-size: 12px; outline: none; }
        button { background: #fff; border: none; padding: 0 18px; border-radius: 12px; font-weight: 900; cursor: pointer; }

        .scene { width: 320px; height: 480px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .scene.flipped { transform: rotateY(180deg); }
        
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 24px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.8); }
        .face.back { transform: rotateY(180deg); background: #fdfdfd; padding: 15px; }

        .stub { height: 35%; background: var(--brand); color: #fff; padding: 25px; display: flex; flex-direction: column; justify-content: center; transition: background 0.6s ease; }
        .dots-container { display: flex; gap: 5px; margin-top: 12px; }
        .sq { width: 12px; height: 12px; border: 1.5px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.3); border-radius: 3px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 12px var(--gold); }

        .perfor { height: 4px; border-top: 6px dotted #ddd; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:40px; height:40px; background:var(--bg); border-radius:50%; top:-20px; }
        .perfor::before { left:-30px; } .perfor::after { right:-30px; }

        .main { flex: 1; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 20px; font-weight: 900; color: #000; height: 26px; display: flex; gap: 1px; margin-top: 4px; }
        .char { width: 15px; height: 24px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; box-shadow: inset 0 0 2px rgba(0,0,0,0.1); }
        
        .label { font-size: 8px; font-weight: 900; color: #999; text-transform: uppercase; letter-spacing: 0.5px; }
        .date-visual { color: var(--blue-txt); font-weight: 900; text-align: right; line-height: 1; }
        
        #bc { width: 120px; height: 40px; margin-top: 10px; opacity: 0.8; cursor: pointer; transition: 0.3s; }
        #bc:hover { opacity: 1; }

        .ticker { width: 320px; height: 40px; background: #000; border: 1px solid #222; border-radius: 8px; margin-top: 20px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 12px; letter-spacing: 1.5px; box-shadow: inset 0 0 10px rgba(255, 215, 0, 0.1); }

        @media (orientation: landscape) { 
            .scene { width: 580px; height: 280px; } 
            .face { flex-direction: row !important; } 
            .stub { width: 32% !important; height: 100% !important; } 
            .perfor { width: 4px !important; height: 100% !important; border-left: 6px dotted #ddd !important; border-top: none !important; } 
            .perfor::before { left:-20px; top:-30px; } .perfor::after { left:-20px; bottom:-30px; top: auto; }
            .main { width: 68% !important; } 
            .ticker { width: 580px; } 
        }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER CITY OR AIRPORT">
        <button onclick="startSearch()">FLY</button>
    </div>
    
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; font-weight:900; opacity:0.6; letter-spacing:2px;">RADAR SCANNING</div>
                <div style="font-size:11px; font-weight:900; margin-top:8px; height: 14px;" id="airl">WAITING CONTACT...</div>
                <div style="font-size:75px; font-weight:900; letter-spacing:-5px; margin:5px 0; line-height: 0.8;">19A</div>
                <div class="dots-container" id="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #000; font-weight: 900; font-size: 14px; border: 2px solid #000; padding: 4px 12px; border-radius: 6px; align-self: flex-start; letter-spacing: 1px;">BOARDING PASS</div>
                
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin: 15px 0;">
                    <div><span class="label" id="icao-label">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span class="label" id="dist-label">DISTANCE</span><div id="f-dist" class="flap" style="color:#555"></div></div>
                    <div><span class="label">FLIGHT IDENT</span><div id="f-call" class="flap"></div></div>
                    <div><span class="label">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:55px; transition:2s cubic-bezier(0.175, 0.885, 0.32, 1.275); filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">✈</div>
                    <div class="date-visual">
                        <div id="f-line1" style="font-size: 14px;">-- --- ----</div>
                        <div id="f-line2" style="font-size: 32px;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=READY" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>

        <div class="face back">
            <div style="height:100%; border:2px dashed #eee; border-radius:20px; padding:25px; display:flex; flex-direction:column; background: #fff;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span class="label">ALTITUDE (MSL)</span><div id="b-alt" class="flap"></div></div>
                    <div><span class="label" id="spd-label">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                
                <div style="border: 4px double var(--blue-txt); color: var(--blue-txt); padding: 15px; border-radius: 12px; transform: rotate(-8deg); align-self: center; margin-top: 40px; text-align: center; font-weight: 900; background: rgba(52, 168, 201, 0.05);">
                    <div style="font-size:10px; letter-spacing: 2px;">SECURITY CHECKED</div>
                    <div id="b-date-line1" style="margin: 5px 0;">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:28px;">--.--</div>
                    <div style="font-size:9px; margin-top:8px; opacity: 0.8;">RADAR CONTACT V94</div>
                </div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">INITIALIZING RADAR SYSTEM...</div>

    <script>
        let pos = null, act = null, isTest = false, weather = null;
        let toggleState = true; 
        let tickerMsg = [], tickerIdx = 0;
        let audioCtx = null;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(900, audioCtx.currentTime); 
                gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.6);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.6);
            } catch(e) {}
        }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const limit = isTicker ? 30 : 8;
            const target = text.toUpperCase().padEnd(limit, ' ');
            container.innerHTML = '';
            [...target].forEach((char) => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let count = 0, max = 15 + Math.floor(Math.random() * 30); 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { clearInterval(interval); span.innerHTML = (char === ' ') ? '&nbsp;' : char; }
                }, 40); 
            });
        }

        setInterval(() => {
            if(act) {
                toggleState = !toggleState;
                document.getElementById('icao-label').innerText = toggleState ? "AIRCRAFT ICAO" : "REGISTRATION";
                applyFlap('f-icao', toggleState ? act.icao : act.reg);
                document.getElementById('dist-label').innerText = toggleState ? "DISTANCE" : "EST. CONTACT";
                applyFlap('f-dist', toggleState ? act.dist + " KM" : "ETA " + act.eta + "M");
                document.getElementById('spd-label').innerText = toggleState ? "GROUND SPEED" : "AIRSPEED (KTS)";
                applyFlap('b-spd', toggleState ? act.spd + " KMH" : act.kts + " KTS");
            }
        }, 12000);

        function updateTicker() { if (tickerMsg.length > 0) { applyFlap('tk', tickerMsg[tickerIdx], true); tickerIdx = (tickerIdx + 1) % tickerMsg.length; } }
        setInterval(updateTicker, 10000);

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
                    
                    for(let i=1; i<=5; i++) {
                        const threshold = 200 - (i * 35);
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }

                    if(!act || act.icao !== f.icao) {
                        playPing();
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        toggleState = true;
                        applyFlap('f-icao', f.icao); applyFlap('f-dist', f.dist + " KM");
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }
                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    act = f;
                    tickerMsg = [`SQUAWKING: ${f.call}`, `REG: ${f.reg}`, `RANGE: ${f.dist} KM`, `SKY: ${weather.sky}`];
                } else { 
                    tickerMsg = [`SEARCHING TRAFFIC...`, `TEMP: ${weather.temp}`, `CONDITIONS: ${weather.sky}`];
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                    act = null;
                }
            } catch(e) {}
        }

        function startSearch() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`).then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } }); }
        }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }
        function hideUI() { document.getElementById('ui').classList.add('hide'); setTimeout(() => { update(); setInterval(update, 15000); }, 600); }
        
        navigator.geolocation.getCurrentPosition(p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, () => { applyFlap('tk', 'PLEASE ENTER LOCATION', true); }, { timeout: 5000 });
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
