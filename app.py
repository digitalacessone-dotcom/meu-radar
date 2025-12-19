from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 25.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    start_lat, start_lon = radians(lat1), radians(lon1)
    end_lat, end_lon = radians(lat2), radians(lon2)
    d_lon = end_lon - start_lon
    y = sin(d_lon) * cos(end_lat)
    x = cos(start_lat) * sin(end_lat) - sin(start_lat) * cos(end_lat) * cos(d_lon)
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Radar Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                width: 100vw; height: 100vh; height: -webkit-fill-available;
                font-family: 'Courier New', monospace; overflow: hidden;
            }
            html { height: -webkit-fill-available; }

            #search-box { 
                display: none; width: 90%; max-width: 500px; background: rgba(0,0,0,0.5);
                padding: 15px; border-radius: 12px; margin-bottom: 20px; 
                border: 2px solid var(--warning-gold); gap: 10px; z-index: 100;
            }
            #search-box input { flex: 1; background: #000; border: 1px solid var(--warning-gold); padding: 12px; color: var(--warning-gold); border-radius: 6px; font-weight: bold; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 20px; font-weight: 900; border-radius: 6px; cursor: pointer; }

            /* ESTILO DAS PALHETAS (SPLIT-FLAP) */
            .letter-slot { 
                display: inline-block; 
                min-width: 0.7em; 
                height: 1.2em;
                line-height: 1.2em;
                text-align: center; 
                position: relative;
                color: var(--warning-gold);
                background: #111; /* Fundo preto da plaqueta */
                margin: 0 1px;
                border-radius: 3px;
                border-bottom: 1px solid #000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.5);
            }
            
            .flapping { 
                animation: mechanical-flip 0.1s ease-in-out;
            }

            @keyframes mechanical-flip {
                0% { transform: scaleY(1); filter: brightness(1.2); }
                50% { transform: scaleY(0.5); filter: brightness(0.7); }
                100% { transform: scaleY(1); filter: brightness(1.2); }
            }

            .card { 
                background: var(--air-blue); width: 92%; max-width: 620px;
                border-radius: 15px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
                overflow: hidden; flex-shrink: 0;
            }

            .notch { position: absolute; width: 30px; height: 30px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -15px; } .notch-right { right: -15px; }

            .header { padding: 12px 0; text-align: center; color: white; font-weight: 900; font-size: 0.9em; display: flex; align-items: center; justify-content: center; gap: 12px; letter-spacing: 2px; }

            .white-area { 
                background: #fdfdfd; margin: 0 8px; position: relative; 
                display: flex; padding: 25px 15px; min-height: 240px; border-radius: 3px; 
            }

            .col-left { flex: 1; border-right: 1px dashed #ccc; padding-right: 15px; display: flex; flex-direction: column; justify-content: center; }
            .col-right { width: 150px; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #888; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 1px; }
            .value { font-size: 1.3em; font-weight: 900; margin-bottom: 15px; min-height: 1.3em; display: flex; flex-wrap: wrap; }
            
            #compass { display: inline-block; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); color: var(--warning-gold); font-size: 1.2em; }
            .barcode { height: 45px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 10px 0; border: 1px solid #ddd; }
            .footer { padding: 0 0 15px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 8px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 10px; }
            .status-msg { color: var(--warning-gold); font-size: 0.75em; font-weight: bold; text-transform: uppercase; text-align: center; padding: 0 10px; min-height: 1.2em; }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="CITY OR ZIP CODE...">
            <button onclick="buscarEndereco()">GO</button>
        </div>

        <div class="card" onclick="enableAudio()">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header">✈ BOARDING BOARD ✈</div>
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value"></div></div>
                    <div><div class="label">AIRCRAFT DISTANCE</div><div id="dist_body" class="value"></div></div>
                    <div><div class="label">ALTITUDE (MSL)</div><div id="alt" class="value"></div></div>
                </div>
                <div class="col-right">
                    <div><div class="label">SQUAWK</div><div id="squawk" class="value">----</div></div>
                    <div><div class="label">BEARING</div><div class="value" style="margin-bottom:0;"><span id="compass">↑</span></div></div>
                    <a id="map-link" style="text-decoration:none; width:100%;" target="_blank"><div class="barcode"></div></a>
                    <div id="signal-bars" style="color:var(--air-blue); font-size:11px; font-weight:900; margin-top:5px;">[ ▯▯▯▯▯ ]</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg"></div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;
            let lastHex = null;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:-";
            let audioCtx = null;

            function enableAudio() { if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }

            function playTick() {
                if (!audioCtx) return;
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'square';
                osc.frequency.setValueAtTime(100, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.02, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.02);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.02);
            }

            function playDetectionBip() {
                if (!audioCtx) return;
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.5);
            }

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                const newText = String(newValue).toUpperCase();
                
                // Ajusta o número de plaquetas
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span");
                    s.className = "letter-slot";
                    s.innerText = " ";
                    container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) {
                    container.removeChild(container.lastChild);
                }

                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar) return;

                    // Delay por slot para efeito cascata (50ms por letra)
                    setTimeout(() => {
                        let currentCharIndex = chars.indexOf(slot.innerText);
                        if (currentCharIndex === -1) currentCharIndex = 0;

                        const interval = setInterval(() => {
                            currentCharIndex = (currentCharIndex + 1) % chars.length;
                            const charToShow = chars[currentCharIndex];
                            
                            slot.innerText = charToShow === " " ? "\u00A0" : charToShow;
                            slot.classList.add('flapping');
                            playTick();

                            if (charToShow === targetChar) {
                                clearInterval(interval);
                                setTimeout(() => slot.classList.remove('flapping'), 100);
                            }
                        }, 60); // VELOCIDADE REDUZIDA PARA VER O GIRO (60ms)
                    }, i * 50); 
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status', 'WAITING GPS SIGNAL...');
                
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, err => {
                    document.getElementById('search-box').style.display = "flex";
                    updateWithEffect('status', 'INPUT LOCATION MANUALLY');
                });
            };

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                if(!query) return;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('search-box').style.display = "none";
                    iniciarRadar();
                }
            }

            function iniciarRadar() { 
                setInterval(executarBusca, 10000); 
                executarBusca(); 
                updateWithEffect('status', 'RADAR SCANNING ACTIVE');
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        if (data.hex !== lastHex) { playDetectionBip(); lastHex = data.hex; }
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        updateWithEffect('squawk', data.squawk);
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        let bars = Math.max(1, Math.ceil((25 - data.dist) / 5));
                        document.getElementById('signal-bars').innerText = "[" + "▮".repeat(bars) + "▯".repeat(5-bars) + "]";
                    } else {
                        if(lastHex) {
                            updateWithEffect('callsign', "SEARCHING");
                            updateWithEffect('dist_body', "-- KM");
                            updateWithEffect('alt', "00000 FT");
                            updateWithEffect('squawk', "----");
                            lastHex = null;
                        }
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

