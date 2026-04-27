import os
from dotenv import load_dotenv
import psycopg2
import cv2
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Users\jordi\Desktop\app_tennis\tessdata"

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),  
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)

cur = conn.cursor()

# 📁 RUTA IMÁGENES
ruta = r"C:\Users\jordi\Pictures\Screenshots\jugadores"

# 🧠 LIMPIAR TEXTO OCR
def limpiar_lineas(texto):
    return [l.strip() for l in texto.split("\n") if l.strip()]

# 🎯 PROCESAR JUGADORES
def procesar_bloques(lineas):
    jugadores = []
    i = 0

    while i < len(lineas) - 3:
        try:
            nombre_completo = lineas[i]
            club = lineas[i+1]
            licencia = lineas[i+2]
            ano = lineas[i+3]

            if licencia.isdigit() and len(licencia) >= 6 and ano.isdigit():

                partes = nombre_completo.split()

                nombre = partes[0]
                apellido1 = partes[1] if len(partes) > 1 else ""
                apellido2 = " ".join(partes[2:]) if len(partes) > 2 else ""

                jugadores.append({
                    "nombre": nombre,
                    "apellido1": apellido1,
                    "apellido2": apellido2,
                    "club": club,
                    "licencia": licencia,
                    "ano": int(ano)
                })

                i += 4
            else:
                i += 1

        except:
            i += 1

    return jugadores

# 🚀 PROCESAR TODAS LAS IMÁGENES
for archivo in os.listdir(ruta):
    if not archivo.lower().endswith(".png"):
        continue

    path = os.path.join(ruta, archivo)

    print(f"Procesando: {archivo}")

    img = cv2.imread(path)

    h, w, _ = img.shape

    img_izq = img[:, :int(w * 0.65)]
    img_der = img[:, int(w * 0.65):]

    texto_izq = pytesseract.image_to_string(img_izq, lang="spa")
    texto_der = pytesseract.image_to_string(img_der, lang="spa")

    lineas_izq = [l.strip() for l in texto_izq.split("\n") if l.strip()]

    nombres = []
    clubs = []

    i = 0
    while i < len(lineas_izq) - 1:
        nombres.append(lineas_izq[i])
        clubs.append(lineas_izq[i + 1])
        i += 2

    lineas_der = [l.strip() for l in texto_der.split("\n") if l.strip()]
    numeros = [l for l in lineas_der if l.isdigit()]

    mitad = len(numeros) // 2
    licencias = numeros[:mitad]
    anos = [int(x) for x in numeros[mitad:]]

    jugadores = []

    for i in range(min(len(nombres), len(clubs), len(licencias), len(anos))):
        partes = nombres[i].split()

        jugadores.append({
            "nombre": partes[0],
            "apellido1": partes[1] if len(partes) > 1 else "",
            "apellido2": " ".join(partes[2:]) if len(partes) > 2 else "",
            "club": clubs[i],
            "licencia": licencias[i],
            "ano": anos[i]
        })

    for j in jugadores:
        cur.execute("""
            INSERT INTO jugadores_importados
            (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            j["nombre"],
            j["apellido1"],
            j["apellido2"],
            j["club"],
            j["ano"],
            j["licencia"]
        ))

# 💾 GUARDAR
conn.commit()
cur.close()
conn.close()

print("Jugadores importados a Supabase 🚀")
