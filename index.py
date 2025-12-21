# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V75 - Foco no Efeito Placar (Split-Flap)
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
        return f"TEMP: {curr['temperature_2m']}C"
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
            return jsonify({"flight": {"icao": "E4953E", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 10.5, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time}, "weather": "TEST"})

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
                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1),
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0),
                            "spd": int(s.get('gs', 0) * 1.852), "hd": int(s.get('track', 0)), "date": now_date, "time": now_time
                        })
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "weather": get_weather(lat, lon), "date": now_date, "time": now_time})
    except: return jsonify({"flight": None})

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }

        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; }
        #ui.hide { display: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }

        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s; }
        .scene.flipped { transform: rotateY(180deg); }
        
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #f4f4f4; padding: 15px; }

        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; }
        .dots-container { display: flex !important; flex-direction: row !important; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }

        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }

        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .bp-title { color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 3px 10px; border-radius: 4px; align-self: flex-start; }
        .label { font-size: 7px; font-weight: 900; color: #bbb; text-transform: uppercase; letter-spacing: 1px; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 22px; display: flex; overflow: hidden; }
        .char { width: 11px; text-align: center; background: #eee; margin-right: 1px; border-radius: 2px; }

        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 0.95; }
        .stamp { border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 10px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 20px; text-align: center; font-weight: 900; }
        
        #bc { width: 110px; height: 35px; opacity: 0.15; filter: grayscale(1); transition: 0.5s; }
        .ticker { width: 300px; height: 25px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 9px; }

        @media (orientation: landscape) { .scene { width: 550px; height: 260px; } .face { flex-direction: row !important; } .stub { width: 30% !important; height: 100% !important; } .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } .main { width: 70% !important; } .ticker { width: 550px; } }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="DIGITE O LOCAL">
        <button onclick="startSearch()">SCAN</button>
    </div>

    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900; opacity:0.7;">RADAR SCANNING</div>
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">SEARCHING...</div>
                <div style="font-size:65px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div class="dots-container">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div class="bp-title">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div><span class="label">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span class="label">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div style="grid-column:span 2;"><span class="label">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div>
                        <div class="date-visual">
                            <div id="f-line1">-- --- ----</div>
                            <div id="f-line2">--.--</div>
                        </div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:20px; display:flex; flex-direction:column; position:relative;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span class="label">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span class="label">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div class="stamp">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V75</div>
                </div>
                <div style="margin-top:auto; color:#ccc; font-size:10px; text-align:right;">BACKSIDE_VERIFICATION</div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">AGUARDANDO LOCALIZAÇÃO...</div>

    <script>
        let pos = null, act = null, isTest = false;
        const audio = new (window.AudioContext || window.webkitAudioContext)();
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.↑↓↔ ";

        function bip() {
            const o = audio.createOscillator(); const g = audio.createGain();
            o.connect(g); g.connect(audio.destination); o.frequency.value = 850;
            g.gain.setValueAtTime(0.05, audio.currentTime); o.start(); o.stop(audio.currentTime + 0.1);
        }

        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }

        function flap(id, txt) {
            const el = document.getElementById(id); if(!el) return;
            const newTxt = txt.toUpperCase();
            el.innerHTML = "";
            [...newTxt].forEach((c, i) => {
                const s = document.createElement('span'); s.className="char"; s.innerText = "-"; el.appendChild(s);
                let n = 0; 
                const iv = setInterval(() => {
                    s.innerText = chars[Math.floor(Math.random()*chars.length)];
                    if(n++ > 10 + i) { clearInterval(iv); s.innerText = c; }
                }, 40);
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
                    document.getElementById('b-date-line1').innerText = f.date;
                    document.getElementById('b-date-line2').innerText = f.time;
                    
                    if(!act || act.icao !== f.icao) {
                        bip();
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        flap('f-icao', f.icao); 
                        flap('f-call', f.call);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        document.getElementById('bc').style.opacity = "0.8";
                    }
                    // Sempre roda flap na distância e verso
                    flap('f-dist', f.dist + "KM");
                    flap('b-alt', f.alt + "FT"); 
                    flap('b-spd', f.spd + "KMH");
                    
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).classList.toggle('on', f.dist <= (250 - i*40));
                    act = f;
                    document.getElementById('tk').innerText = `LOCALIZADO: ${f.call} - ${f.dist}KM`;
                } else {
                    document.getElementById('tk').innerText = `BUSCANDO... | ${d.weather || 'OFFLINE'}`;
                }
            } catch(e) { console.error(e); }
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
        setTimeout(() => { if(!pos) document.getElementById('tk').innerText = "IPHONE: DIGITE O LOCAL ACIMA"; }, 5000);
        navigator.geolocation.getCurrentPosition(p => {
            pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI();
        }, () => { document.getElementById('tk').innerText = "POR FAVOR, DIGITE O LOCAL"; }, { timeout: 6000 });
    </script>
</body>
</html>
''')
