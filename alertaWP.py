import requests
import time
from datetime import datetime
from flask import Flask
import threading

# === CONFIGURACIÓN ===
MONEDA = "LTCUSDT"
INTERVALO_MINUTOS = 5
UMBRAL_ALERTA = 5.0  # USD de diferencia para alertar
NUMERO = "5492914228541"
API_KEY = "7577157"

# === VARIABLES GLOBALES ===
precio_maximo = None
precio_minimo = None
ultima_alerta_tipo = None  # Para evitar spam

# === FUNCIONES ===
def obtener_precio():
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={MONEDA}"
    return float(requests.get(url).json()["price"])

def obtener_estadisticas_24h():
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={MONEDA}"
    data = requests.get(url).json()
    return {
        'high': float(data['highPrice']),
        'low': float(data['lowPrice']),
        'change_percent': float(data['priceChangePercent'])
    }

def enviar_whatsapp(mensaje):
    try:
        mensaje_encoded = mensaje.replace(" ", "+").replace("\n", "%0A")
        url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={mensaje_encoded}&apikey={API_KEY}"
        r = requests.get(url)
        print(f"✅ WhatsApp enviado: {mensaje}" if r.status_code == 200 else f"⚠️ Error {r.status_code}")
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

def analizar_movimiento(precio_actual):
    global precio_maximo, precio_minimo, ultima_alerta_tipo
    
    ahora = datetime.now().strftime("%H:%M:%S")
    
    # Inicializar referencias si es la primera vez
    if precio_maximo is None or precio_minimo is None:
        precio_maximo = precio_actual
        precio_minimo = precio_actual
        print(f"🔹 Inicializado: Máx=${precio_maximo:.2f} | Mín=${precio_minimo:.2f}")
        return
    
    # Actualizar máximo y mínimo
    if precio_actual > precio_maximo:
        precio_maximo = precio_actual
        print(f"📈 Nuevo máximo: ${precio_maximo:.2f}")
    
    if precio_actual < precio_minimo:
        precio_minimo = precio_actual
        print(f"📉 Nuevo mínimo: ${precio_minimo:.2f}")
    
    # Verificar BAJADA (desde el máximo)
    bajada = precio_maximo - precio_actual
    if bajada >= UMBRAL_ALERTA and ultima_alerta_tipo != "BAJADA":
        mensaje = (f"🔴 BAJADA IMPORTANTE [{ahora}]\n"
                   f"Precio actual: ${precio_actual:.2f}\n"
                   f"Bajó ${bajada:.2f} desde máximo (${precio_maximo:.2f})")
        enviar_whatsapp(mensaje)
        ultima_alerta_tipo = "BAJADA"
        # Resetear mínimo para próxima subida
        precio_minimo = precio_actual
        print(f"🔄 Mínimo reseteado a ${precio_minimo:.2f}")
    
    # Verificar SUBIDA (desde el mínimo)
    subida = precio_actual - precio_minimo
    if subida >= UMBRAL_ALERTA and ultima_alerta_tipo != "SUBIDA":
        mensaje = (f"🟢 SUBIDA IMPORTANTE [{ahora}]\n"
                   f"Precio actual: ${precio_actual:.2f}\n"
                   f"Subió ${subida:.2f} desde mínimo (${precio_minimo:.2f})")
        enviar_whatsapp(mensaje)
        ultima_alerta_tipo = "SUBIDA"
        # Resetear máximo para próxima bajada
        precio_maximo = precio_actual
        print(f"🔄 Máximo reseteado a ${precio_maximo:.2f}")

def iniciar_bot():
    print("🚀 Bot de Alertas LTC iniciado")
    enviar_whatsapp("🤖 Bot LTC activo - Alertas de movimientos ±$5")
    
    while True:
        try:
            precio_actual = obtener_precio()
            stats = obtener_estadisticas_24h()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Precio: ${precio_actual:.2f} "
                  f"| Máx: ${precio_maximo if precio_maximo else 0:.2f} "
                  f"| Mín: ${precio_minimo if precio_minimo else 0:.2f}")
            
            analizar_movimiento(precio_actual)
            time.sleep(INTERVALO_MINUTOS * 60)
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(60)

# === FLASK APP PARA RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    estado = f"Precio actual: ${precio_maximo if precio_maximo else 'cargando...'}"
    return f"Bot LTC Alertas activo ✅<br>{estado}"

if __name__ == '__main__':
    threading.Thread(target=iniciar_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)