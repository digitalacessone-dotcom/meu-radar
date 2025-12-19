from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

# Funções matemáticas permanecem iguais para garantir a precisão do radar
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
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Premium Pass</title>
        <style>
            :root { --air-blue: #226488; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: #f0f4f7; margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Helvetica Neue', Arial, sans-serif; overflow: hidden;
            }

            .card { 
                background: white; width: 95%; max-width: 850px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
                display: flex; overflow: hidden; border: 1px solid #ddd;
            }

            /* MEIAS-LUAS GRANDES */
            .notch { 
                position: absolute; width: 80px; height: 80px; 
                background: #f0f4f7; border-radius: 50%; 
                top: 50%; transform: translateY(-50%); z-index: 30; 
            }
            .notch-left { left: -40px; }
            .notch-right { right: -40px; }

            /* SEÇÃO ESQUERDA (STUB) */
            .left-stub {
                width: 25%; background: var(--air-blue); color: white;
                padding: 20px; display: flex; flex-direction: column;
                border-right: 2px dashed rgba(255,255,255,0.3); position: relative;
            }
            .left-stub .seat-num { font-size: 4em; font-weight: 900; margin-top: 20px; line-height: 1; }
            .left-stub .seat-label { font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }

            /* SEÇÃO DIREITA (CORPO) */
            .main-ticket { flex: 1; display: flex; flex-direction: column; }

            .header-bar { 
                background: var(--air-blue); height: 80px; display: flex; 
                align-items: center; justify-content: space-between; padding: 0 40px; color: white;
            }
            .header-bar h1 { font-size: 1.5em; letter-spacing: 5px; margin: 0; }
            .plane-icon { font-size: 2em; opacity: 0.8; }

            /* CONTEÚDO DOS DADOS */
            .content-area { 
                padding: 30px 50px; display: flex; flex: 1; background: white;
            }
            .col { display: flex; flex-direction: column; justify-content: space-around; }
            .col-data { flex: 2; border-right: 1px solid #eee; }
            .col-side { flex: 1; padding-left: 30px; align-items: center; }

            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); min-height: 1.2em; display: flex; }

            /* TERMINAL DE STATUS NO RODAPÉ */
            .terminal-footer { 
                background: #000; color: var(--warning-gold); 
                padding: 10px 40px; font-family: 'Courier New', monospace; font-size: 0.9em;
            }

            /* EFEITO FLAP */
            .letter-slot { display: inline-block; min-width: 0.6em; text-align: center; }
            .flapping { animation: flap 0.06s infinite; }
            @keyframes flap { 50% { transform: scaleY(0.5); opacity: 0.5; } }

            #compass { font-size: 2em; transition: transform 0.8s ease; display: inline-block; color: #ff8c00; }
            .barcode { width: 150px; height: 50px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 5px); margin-top: 20px; opacity: 0.7; }
        </style>
    </head>
    <body>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>

            <div class="left-stub">
                <div class="label" style="color: rgba(255,255,255,0.7)">Your Radar</div>
                <div class="seat-label">Seat Number:</div>
                <div class="seat-num">19 A</div>
                <div class="seat-label" style="margin-top: auto;">First Class / ATC</div>
            </div>

            <div class="main-ticket">
                <div class="header-bar">
                    <span class="plane-icon">✈</span>
                    <h1>BOARDING BOARD</h1>
                    <span class="plane-icon">✈</span>
                </div>

                <div class="content-area">
                    <div class="col col-data">
                        <div>
                            <div class="label">Ident / Callsign</div>
                            <div id="callsign" class="value"></div>
                        </div>
                        <div>
                            <div class="label">Aircraft Distance</div>
                            <div id="dist_body" class="value"></div>
                        </div>
                        <div>
                            <div class="label">Altitude (MSL)</div>
                            <div id="alt" class="value"></div>
                        </div>
                    </div>

                    <div class="col col-side">
                        <div class="label">Type</div>
                        <div id="type_id" class="value">----</div>
                        <div class="label" style="margin-top: 20px;">Bearing</div>
                        <div id="compass">↑</div>
                        <div class="barcode"></div>
                    </div>
                </div>

                <div class="terminal-footer">
                    <div id="status">> RADAR INITIALIZING...</div>
                </div>
            </div>
        </div>

        <script>
            // Lógica de animação e busca idêntica ao seu código anterior, 
            // adaptada para os novos IDs de elemento.
            let latAlvo = null, lonAlvo = null;
            let currentTarget = null;
            let statusIndex = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                if (!container) return;
                const newText = String(newValue).toUpperCase();
                
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span"); s.className = "letter-slot"; s.innerHTML = "&nbsp;"; container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) { container.removeChild(container.lastChild); }

                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar) return;
                    let cycles = 0;
                    const interval = setInterval(() => {
                        slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                        slot.classList.add('flapping');
                        if (++cycles >= 10 + i) {
                            clearInterval(interval);
                            slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                            slot.classList.remove('flapping');
                        }
                    }, 60);
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                });

                setInterval(() => {
                    const statusElem = document.getElementById('status');
                    if(!currentTarget) {
                        const msgs = ["> SCANNING AIRSPACE...", "> SYSTEM OK", "> WAITING FOR SIGNAL"];
                        statusElem.innerText = msgs[statusIndex % msgs.length];
                    } else {
                        statusElem.innerText = `> TARGET: ${currentTarget.callsign} | SPEED: ${currentTarget.speed} KTS`;
                    }
                    statusIndex++;
                }, 5000);
            };

            function iniciarRadar() { setInterval(executarBusca, 8000); executarBusca(); }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        currentTarget = data;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('type_id', data.type);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

# O restante das rotas Python se mantém igual.











