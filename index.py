# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# ==========================================
# CONFIGURAÇÕES TÉCNICAS V99.0
# ==========================================
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    """Retorna o horário de Brasília (UTC-3)"""
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    """Mapeamento de códigos WMO da Open-Meteo"""
    mapping = {
        0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST",
        45: "FOG", 51: "LIGHT DRIZZLE", 61: "RAIN", 80: "SHOWERS"
    }
    return mapping.get(code, "CONDITIONS OK")

def get_weather(lat, lon):
    """Busca dados meteorológicos reais da posição do radar"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,visibility"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        vis_km = int(curr.get('visibility', 10000) / 1000)
        return {
            "temp": f"{int(curr['temperature_2m'])}C",
            "sky": get_weather_desc(curr['weather_code']),
            "vis": f"{vis_km}KM"
        }
    except Exception:
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    """Busca tráfego aéreo em múltiplas APIs para redundância"""
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 RadarBoard', 'Accept': 'application/json'}
    random.shuffle(endpoints)
    
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                return r.json().get('aircraft', [])
        except Exception:
            continue
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
        
        # Modo de Teste com aeronave Militar
        if test:
            return jsonify({
                "flight": {
                    "icao": "AE0802", "reg": "06-6164", "call": "RCH144", 
                    "airline": "US AIR FORCE", "color": "#1a1d21", "dist": 15.2, 
                    "alt": 32000, "spd": 830, "hd": 245, "date": now_date, 
                    "time": now_time, "route": "RMS-DOV", "eta": 12, "kts": 448, "vrate": -512
                },
                "weather": w, "date": now_date, "time": now_time
            })
        
        data = fetch_aircrafts(lat, lon)
        found = None
        
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if isinstance(slat, (int, float)) and isinstance(slon, (int, float)):
                    # Cálculo de distância Haversine
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip()
                        airline, color = "PRIVATE", "#444"
                        
                        # Identificação de operadoras
                        if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        elif s.get('mil') == "1": airline, color = "MILITARY", "#1a1d21"
                        
                        spd_kts = int(s.get('gs', 0) or 0)
                        spd_kmh = int(spd_kts * 1.852)
                        
                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(),
                            "reg": s.get('r', 'N/A').upper(),
                            "call": call,
                            "airline": airline,
                            "color": color,
                            "dist": round(d, 1),
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0),
                            "spd": spd_kmh,
                            "kts": spd_kts,
                            "hd": int(s.get('track', 0) or 0),
                            "date": now_date,
                            "time": now_time,
                            "route": s.get('route', "--- ---"),
                            "eta": round((d / (spd_kmh or 1)) * 60),
                            "vrate": int(s.get('baro_rate', 0) or 0)
                        })
            
            if proc:
                found = sorted(proc, key=lambda x: x['dist'])[0]
                
        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time})
    except Exception as e:
        return jsonify({"flight": None, "error": str(e)})

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Radar Boarding Pass</title>
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        
        body { 
            background: var(--bg); 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex; flex-direction: column; align-items: center; justify-content: center; 
            min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; 
        }

        /* UI de Busca */
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 20px; z-index: 500; transition: 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; transform: translateY(-20px); }
        input { flex: 1; padding: 15px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 12px; outline: none; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        button { background: #fff; border: none; padding: 0 20px; border-radius: 12px; font-weight: 900; cursor: pointer; transition: 0.3s; }
        button:active { transform: scale(0.95); }

        /* Cena 3D do Cartão */
        .scene { width: 320px; height: 480px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .scene.flipped { transform: rotateY(180deg); }

        /* Faces do Cartão com Efeito Gold Neon */
        .face { 
            position: absolute; width: 100%; height: 100%; backface-visibility: hidden; 
            border-radius: 24px; background: #fff; display: flex; flex-direction: column; overflow: hidden; 
            border: 2px solid var(--gold);
            box-shadow: 0 0 15px rgba(255,215,0,0.3), 0 0 30px rgba(255,215,0,0.1), 0 20px 50px rgba(0,0,0,0.5); 
        }
        .face.back { transform: rotateY(180deg); background: #f4f4f4; padding: 20px; }

        /* Seção Canhoto (Stub) */
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: background 0.6s; }
        .dots-container { display: flex; gap: 6px; margin-top: 10px; }
        .sq { width: 12px; height: 12px; border: 1.5px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.2); border-radius: 3px; transition: 0.4s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 12px var(--gold); }

        /* Perfuração Visual */
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; margin: 0 5px; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:34px; height:34px; background:var(--bg); border-radius:50%; top:-17px; }
        .perfor::before { left:-28px; } .perfor::after { right:-28px; }

        /* Seção Principal */
        .main { flex: 1; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: "Courier New", monospace; font-size: 19px; font-weight: 900; color: #000; height: 26px; display: flex; gap: 2px; }
        .char { width: 15px; height: 24px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        
        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 1; text-align: right; }
        #bc { width: 120px; height: 40px; opacity: 0.2; filter: grayscale(1); cursor: pointer; margin-top: 8px; transition: 0.3s; }
        #bc:hover { opacity: 0.8; filter: none; }

        /* Ticker Digital */
        .ticker { 
            width: 320px; height: 35px; background: #000; border-radius: 8px; margin-top: 20px; 
            display: flex; align-items: center; justify-content: center; 
            color: var(--gold); font-family: "Courier New", monospace; font-size: 11px; 
            letter-spacing: 1px; border: 1px solid #222;
        }

        @media (orientation: landscape) {
            .scene { width: 580px; height: 280px; }
            .face { flex-direction: row !important; }
            .stub { width: 30% !important; height: 100% !important; }
            .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; }
            .main { width: 70% !important; }
            .ticker { width: 580px; }
        }
    </style>
</head>
<body onclick="handleFlip(event)">

    <div id="ui">
        <input type="text" id="in" placeholder="CITY OR IATA CODE">
        <button onclick="startSearch()">CHECK-IN</button>
    </div>

    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; font-weight:900; opacity:0.6; letter-spacing:1px;">RADAR SCANNING</div>
                <div style="font-size:11px; font-weight:900; margin-top:6px;" id="airl">WAITING DATA...</div>
                <div style="font-size:70px; font-weight:900; letter-spacing:-5px; margin:5px 0; line-height:0.8;">19A</div>
                <div class="dots-container" id="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            
            <div class="perfor"></div>
            
            <div class="main">
                <div style="color:#333; font-weight:900; font-size:12px; border:1.8px solid #333; padding:4px 12px; border-radius:6px; align-self:flex-start; letter-spacing:1px;">BOARDING PASS</div>
                
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-top:15px;">
                    <div><span id="icao-label" style="font-size:7px; font-weight:900; color:#bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-label" style="font-size:7px; font-weight:900; color:#bbb;">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div><span style="font-size:7px; font-weight:900; color:#bbb;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size:7px; font-weight:900; color:#bbb;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:10px;">
                    <div id="arr" style="font-size:50px; transition:1.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);">✈</div>
                    <div class="date-visual">
                        <div id="f-line1">-- --- ----</div>
                        <div id="f-line2" style="font-size:24px;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=RADAR" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>

        <div class="face back">
            <div style="height:100%; border:1.5px dashed #ccc; border-radius:18px; padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size:7px; font-weight:900; color:#bbb;">ALTITUDE (FT)</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="spd-label" style="font-size:7px; font-weight:900; color:#bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                
                <div style="border:3px double var(--blue-txt); color:var(--blue-txt); padding:15px; border-radius:12px; transform:rotate(-8deg); align-self:center; text-align:center; font-weight:900; background:rgba(52,168,201,0.05);">
                    <div style="font-size:9px; letter-spacing:1px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:26px;">--.--</div>
                    <div style="font-size:9px; margin-top:5px; opacity:0.8;">RADAR CONTACT V99.0</div>
                </div>
                
                <div style="font-size:8px; color:#aaa; text-align:center; font-style:italic;">Terms of transport apply. Check airport monitors for gate changes.</div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">INITIALIZING RADAR SYSTEM...</div>

    <script>
        let pos = null, act = null, prevDist = null, isTest = false, weather = null;
        let toggleState = true; 
        let isGhost = false;
        let tickerMsg = [], tickerIdx = 0;
        let audioCtx = null;
        let fDate = "-- --- ----", fTime = "--.--";
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, audioCtx.currentTime); 
                gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.4);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.4);
            } catch(e) {}
        }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const limit = isTicker ? 32 : 8;
            const target = text.toUpperCase().padEnd(limit, ' ');
            container.innerHTML = '';
            
            [...target].forEach((char) => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                
                let count = 0, max = 15 + Math.floor(Math.random() * 25); 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { 
                        clearInterval(interval); 
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char; 
                    }
                }, 40); 
            });
        }

        // Alternância de labels (ICAO vs REG / DIST vs ETA)
        setInterval(() => {
            if(act && !isGhost) {
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
        setInterval(updateTicker, 8000);

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                weather = d.weather;
                
                if(d.flight) {
                    const f = d.flight;
                    isGhost = false;
                    document.getElementById('stb').style.background = f.color;
                    
                    let proximity = "MAINTAINING";
                    if(prevDist !== null) {
                        if(f.dist < prevDist - 0.05) proximity = "CLOSING IN";
                        else if(f.dist > prevDist + 0.05) proximity = "MOVING AWAY";
                    }
                    prevDist = f.dist;

                    let vStatus = f.vrate > 150 ? "CLIMBING" : (f.vrate < -150 ? "DESCENDING" : "LEVEL");

                    if(!act || act.icao !== f.icao) {
                        fDate = f.date; fTime = f.time;
                        playPing();
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        toggleState = true;
                        applyFlap('f-icao', f.icao); applyFlap('f-dist', f.dist + " KM");
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }
                    
                    document.getElementById('f-line1').innerText = fDate;
                    document.getElementById('f-line2').innerText = fTime;
                    document.getElementById('b-date-line1').innerText = fDate;
                    document.getElementById('b-date-line2').innerText = fTime;
                    
                    for(let i=1; i<=5; i++) {
                        const threshold = 190 - ((i-1) * 40);
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }
                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    act = f;

                    tickerMsg = [`V.RATE: ${f.vrate} FPM`, `TRAFFIC: ${vStatus}`, `STATUS: ${proximity}`, `WEATHER: ${weather.temp} ${weather.sky}`];
                    
                } else if(act) { 
                    isGhost = true;
                    prevDist = null;
                    document.getElementById('stb').style.background = "var(--brand)";
                    const g = "SIGNAL LOST / GHOST MODE";
                    tickerMsg = [g, "SEARCHING...", `TEMP: ${weather.temp}`, `VIS: ${weather.vis}`, weather.sky];
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                } else {
                    tickerMsg = ["SCANNING SKY...", `LOCAL TEMP: ${weather.temp}`, `SKY: ${weather.sky}`, "READY FOR CHECK-IN"];
                }
            } catch(e) {}
        }

        function startSearch() {
            if (!audioCtx) audioCtx = new AudioContext();
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { 
                fetch("https://nominatim.openstreetmap.org/search?format=json&q="+v)
                .then(r=>r.json()).then(d=>{ 
                    if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } 
                }); 
            }
        }

        function handleFlip(e) { 
            if(!e.target.closest('#ui') && !e.target.closest('#bc')) 
                document.getElementById('card').classList.toggle('flipped'); 
        }

        function openMap(e) { 
            e.stopPropagation(); 
            if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); 
        }

        function hideUI() { 
            document.getElementById('ui').classList.add('hide'); 
            setTimeout(() => { 
                document.getElementById('ui').style.display = 'none';
                update(); 
                setInterval(update, 15000); 
            }, 800); 
        }

        navigator.geolocation.getCurrentPosition(p => { 
            pos = {lat:p.coords.latitude, lon:p.coords.longitude}; 
            hideUI(); 
        }, () => { 
            applyFlap('tk', 'MANUAL LOCATION REQUIRED', true); 
        }, { timeout: 6000 });
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
