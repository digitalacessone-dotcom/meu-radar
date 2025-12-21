# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V98.0
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        return {"temp": f"{int(curr['temperature_2m'])}C", "sky": "CONDITIONS OK"}
    except:
        return {"temp": "--C", "sky": "METAR ON"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
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
            # Mistura comercial com Blackbird no modo teste
            is_blackbird = random.random() > 0.5
            if is_blackbird:
                f = {"icao": "SR71", "reg": "61-7972", "call": "BLACKBIRD", "airline": "STRATEGIC RECON", "color": "#000", "is_rare": True, "dist": 5.2, "alt": 85000, "spd": 3500, "hd": 350, "route": "EDW-BEALE", "eta": 1, "vrate": 0, "kts": 1900}
            else:
                f = {"icao": "E4953E", "reg": "PT-MDS", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "is_rare": False, "dist": 10.5, "alt": 35000, "spd": 850, "hd": 120, "route": "GIG-MIA", "eta": 1, "vrate": 1500, "kts": 459}
            return jsonify({"flight": f, "weather": w, "date": now_date, "time": now_time, "is_test": True})
        
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
                        airline, color, is_rare = "PRIVATE", "#444", False
                        # Lógica de raros/militares
                        if s.get('t') in ['H60', 'C130', 'F16', 'F35'] or s.get('mil', False): 
                            airline, color, is_rare = "MILITARY FORCE", "#000", True
                        elif call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), "call": call, "airline": airline, "color": color, "is_rare": is_rare, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": int(s.get('gs', 0)*1.852), "kts": int(s.get('gs', 0)), "hd": int(s.get('track', 0)), "route": "--- ---", "eta": 10, "vrate": int(s.get('baro_rate', 0))})
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time, "is_test": False})
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
        :root { --gold: #FFD700; --bg: #0b0e11; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; transition: opacity 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }

        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s; }
        .scene.flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #f4f4f4; }

        .stub { height: 32%; background: #444; color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: 0.5s; position: relative; }
        .stub.rare { background: #000 !important; color: var(--gold) !important; }
        .stub.rare .sq { border-color: rgba(255,215,0,0.3); }

        .dots-container { display: flex; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }

        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }

        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }

        .ticker { width: 310px; height: 34px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 2px; padding: 0 10px; }
        
        /* Selo Elegante */
        .gold-seal { position: absolute; bottom: 20px; right: 20px; width: 45px; height: 45px; background: radial-gradient(circle, #fff7ad 0%, #ffa200 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 6px; font-weight: 900; color: #7a5d00; border: 1px solid #d4af37; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transform: rotate(15deg); }

        @media (orientation: landscape) { .scene { width: 550px; height: 260px; } .face { flex-direction: row !important; } .stub { width: 30% !important; height: 100% !important; } .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } .main { width: 70% !important; } }
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
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">SEARCHING...</div>
                <div style="font-size:65px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div class="dots-container">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 12px; border: 1.5px solid #333; padding: 2px 8px; border-radius: 4px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENT</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">OP. STATUS</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div style="text-align:right; color:var(--blue-txt); font-weight:900;">
                        <div id="f-date" style="font-size:11px;">-- --- ----</div>
                        <div id="f-time" style="font-size:20px; line-height:1;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING&scale=1" style="height:30px; margin-top:5px; opacity:0.3;">
                    </div>
                </div>
            </div>
        </div>

        <div class="face back">
            <div style="height:100%; border:10px solid #fff; padding:15px; display:flex; flex-direction:column; position:relative;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 10px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 40px; text-align: center; font-weight: 900; width: 180px;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-full">-- --- ----</div>
                    <div id="b-time-big" style="font-size:24px;">--.--</div>
                    <div style="font-size:7px;">RADAR CONTACT V98.0</div>
                </div>

                <div class="gold-seal" id="seal" style="display:none;">AUTHENTIC</div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">INITIALIZING RADAR...</div>

    <script>
        let pos = null, act = null, isTest = false;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ ";

        function applyFlap(id, text) {
            const container = document.getElementById(id);
            if(!container) return;
            const target = text.toUpperCase().padEnd(8, ' ');
            container.innerHTML = '';
            [...target].forEach((char, i) => {
                const span = document.createElement('span');
                span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                
                // Letras param em tempos diferentes e maiores
                let count = 0;
                let max = 30 + (i * 12) + Math.floor(Math.random() * 40); 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { 
                        clearInterval(interval); 
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char; 
                    }
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
                    const stub = document.getElementById('stb');
                    
                    // Lado Esquerdo - Cor e Estilo
                    if(f.is_rare) {
                        stub.classList.add('rare');
                        if(!isTest) {
                            let history = JSON.parse(localStorage.getItem('rare_collection') || '[]');
                            if(!history.includes(f.icao)) {
                                history.push(f.icao);
                                localStorage.setItem('rare_collection', JSON.stringify(history));
                            }
                        }
                    } else {
                        stub.classList.remove('rare');
                        stub.style.background = f.color;
                    }

                    document.getElementById('airl').innerText = f.airline;
                    document.getElementById('f-date').innerText = d.date;
                    document.getElementById('f-time').innerText = d.time;
                    document.getElementById('b-date-full').innerText = d.date;
                    document.getElementById('b-time-big').innerText = d.time;
                    document.getElementById('seal').style.display = 'flex';

                    if(!act || act.icao !== f.icao) {
                        applyFlap('f-icao', f.icao);
                        applyFlap('f-call', f.call);
                        applyFlap('f-route', f.is_rare ? "TOP SECRT" : "ACTIVE");
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}`;
                        document.getElementById('bc').style.opacity = "1";
                    }

                    applyFlap('f-dist', f.dist + "KM");
                    applyFlap('b-alt', f.alt + "FT");
                    applyFlap('b-spd', f.spd + "KMH");
                    
                    for(let i=1; i<=5; i++) {
                        document.getElementById('d'+i).className = (f.dist <= (200 - (i-1)*40)) ? 'sq on' : 'sq';
                    }
                    
                    document.getElementById('tk').innerText = `CONTACT: ${f.call} | REG: ${f.reg} | V.RATE: ${f.vrate} FPM`;
                    act = f;
                }
            } catch(e) { console.log(e); }
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { 
                fetch("https://nominatim.openstreetmap.org/search?format=json&q="+v)
                .then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } }); 
            }
        }

        function handleFlip(e) { 
            if(!e.target.closest('#ui')) document.getElementById('card').classList.toggle('flipped'); 
        }

        function hideUI() { 
            document.getElementById('ui').classList.add('hide'); 
            update(); setInterval(update, 12000); 
        }

        navigator.geolocation.getCurrentPosition(p => { 
            pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); 
        }, () => {}, { timeout: 5000 });
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
