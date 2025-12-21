# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V65
RADIUS_KM = 200 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        cond = "CLEAR" if curr['weather_code'] < 3 else "CLOUDY" if curr['weather_code'] < 50 else "RAINY"
        return f"TEMP: {curr['temperature_2m']}C | {cond}"
    except:
        return "METAR: ONLINE"

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/250"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X)', 'Accept': 'application/json'}
    random.shuffle(endpoints)
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                return r.json().get('aircraft', [])
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
        
        if test:
            return jsonify({"flight": {"icao": "E4953E", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 10.5, "alt": 35000, "spd": 850, "trend": "CRUISE ↔", "hd": 120, "date": now_date, "time": now_time}, "connected": True, "weather": "TEST MODE"})

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
                        
                        v_rate = s.get('baro_rate') or 0
                        phase = "CLIMB ↑" if v_rate > 400 else "DESCENT ↓" if v_rate < -400 else "CRUISE ↔"
                        
                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(),
                            "call": call, "airline": airline, "color": color, "dist": round(d, 1),
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0),
                            "spd": int(s.get('gs', 0) * 1.852),
                            "trend": phase, "hd": int(s.get('track', 0)), "date": now_date, "time": now_time
                        })
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "connected": True, "weather": get_weather(lat, lon), "date": now_date, "time": now_time})
    except:
        return jsonify({"flight": None, "connected": False})

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }

        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; }
        #ui.hide { display: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }

        .scene { width: 290px; height: 440px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .scene.flipped { transform: rotateY(180deg); }
        
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.8); }
        .face.front { transform: translateZ(1px); }
        .face.back { transform: rotateY(180deg) translateZ(1px); background: #f9f9f9; padding: 22px; }

        .stub { height: 32%; background: var(--brand); color: #fff; padding: 22px; position: relative; }
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; margin: 0 10px; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:36px; height:36px; background:var(--bg); border-radius:50%; top:-18px; }
        .perfor::before { left:-30px; } .perfor::after { right:-30px; }

        .main { flex: 1; padding: 18px 22px; display: flex; flex-direction: column; justify-content: space-between; }
        
        .bp-title { color: #333; font-weight: 900; font-size: 14px; letter-spacing: 3px; border: 1.5px solid #333; padding: 2px 8px; border-radius: 4px; margin-bottom: 15px; align-self: flex-start; }

        .label { font-size: 7px; font-weight: 900; color: #bbb; letter-spacing: 1.2px; text-transform: uppercase; }
        .flap { font-family: monospace; font-size: 17px; font-weight: 900; color: #000; height: 22px; display: flex; overflow: hidden; }
        .char { width: 11px; text-align: center; }

        /* QUADRADINHOS RECUPERADOS */
        .dots { display: flex; gap: 5px; position: absolute; bottom: 15px; right: 20px; }
        .sq { width: 7px; height: 7px; border: 1px solid rgba(255,255,255,0.2); }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }

        #bc-container { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; }
        .date-visual { color: var(--blue-txt); font-weight: 800; line-height: 0.95; text-align: left; margin-bottom: 4px; }
        .date-visual .line1 { font-size: 19px; }
        .date-visual .line2 { font-size: 17px; }

        #bc { width: 100px; height: 35px; opacity: 0.1; filter: grayscale(1); transition: 0.5s; cursor: pointer; }
        #arr { font-size: 42px; transition: 1.5s; }
        .ticker { width: 290px; height: 22px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 8px; border: 1px solid #333; }
    </style>
</head>
<body onclick="handleFlip(event)">

    <div id="ui">
        <input type="text" id="in" placeholder="LOCAL (EX: RIO)">
        <button onclick="startSearch()">SCAN</button>
    </div>

    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900;" id="stat">RADAR SCANNING</div>
                <div style="font-size:10px; font-weight:900; opacity:0.8; margin-top:8px;" id="airl">SEARCHING...</div>
                <div style="font-size:70px; font-weight:900; letter-spacing:-5px; margin:2px 0;">19A</div>
                <div class="dots">
                    <div id="d1" class="sq"></div>
                    <div id="d2" class="sq"></div>
                    <div id="d3" class="sq"></div>
                    <div id="d4" class="sq"></div>
                    <div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div class="bp-title">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                    <div><span class="label">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span class="label">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div style="grid-column:span 2;"><span class="label">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr">✈</div>
                    <div id="bc-container">
                        <div class="date-visual">
                            <div class="line1" id="f-line1">-- --- ----</div>
                            <div class="line2" id="f-line2">--.--</div>
                        </div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:18px; display:flex; flex-direction:column; gap:15px;">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div><span class="label">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div style="color:var(--blue-txt); font-weight:900; font-size:11px; text-align:right;" id="b-date">RADAR CONTACT<br>--/--/----</div>
                </div>
                <div><span class="label">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                <div><span class="label">FLIGHT PHASE</span><div id="b-trend" class="flap"></div></div>
                <div style="margin-top:auto; font-size:7px; color:#bbb; text-align:center; font-family:monospace;">TRACKED VIA ADS-B NETWORK V65</div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">CONECTANDO...</div>

    <script>
        let pos = null, act = null, isTest = false;
        const audio = new (window.AudioContext || window.webkitAudioContext)();

        function bip() {
            [0, 0.15].forEach(t => {
                const o = audio.createOscillator(); const g = audio.createGain();
                o.connect(g); g.connect(audio.destination);
                o.type = 'square'; o.frequency.value = 850;
                g.gain.setValueAtTime(0.04, audio.currentTime + t);
                o.start(audio.currentTime + t); o.stop(audio.currentTime + t + 0.08);
            });
        }

        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }

        function flap(id, txt) {
            const el = document.getElementById(id); if(!el) return;
            el.innerHTML = "";
            [...txt.toUpperCase()].forEach((c, i) => {
                const s = document.createElement('span'); s.className="char"; el.appendChild(s);
                let n = 0;
                const iv = setInterval(() => {
                    s.innerText = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.↑↓↔"[Math.floor(Math.random()*42)];
                    if(n++ > 10+i) { clearInterval(iv); s.innerText = c; }
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
                    document.getElementById('f-line1').innerText = f.date;
                    document.getElementById('f-line2').innerText = f.time;
                    if(!act || act.icao !== f.icao) {
                        bip();
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        flap('f-icao', f.icao); flap('f-call', f.call);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        document.getElementById('bc').style.opacity = "0.8";
                        document.getElementById('bc').style.filter = "none";
                    }
                    flap('f-dist', f.dist + "KM");
                    flap('b-alt', f.alt + " FT"); flap('b-spd', f.spd + " KMH"); flap('b-trend', f.trend);
                    document.getElementById('b-date').innerHTML = `RADAR CONTACT<br>${f.date} ${f.time}`;
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    
                    // Lógica dos quadradinhos
                    for(let i=1; i<=5; i++) {
                        document.getElementById('d'+i).classList.toggle('on', f.dist <= (250 - i*40));
                    }
                    
                    act = f;
                    document.getElementById('tk').innerText = `RADAR ATIVO: ${f.call}`;
                } else {
                    document.getElementById('tk').innerText = `BUSCANDO... | ${d.weather}`;
                }
            } catch(e) { document.getElementById('tk').innerText = "ERRO DE SINAL"; }
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else {
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`).then(r=>r.json()).then(d=>{
                    if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); }
                });
            }
        }

        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 10000); }

        navigator.geolocation.getCurrentPosition(p => {
            pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI();
        }, () => { document.getElementById('tk').innerText = "GPS OFF - DIGITE CIDADE"; });
    </script>
</body>
</html>
''')
