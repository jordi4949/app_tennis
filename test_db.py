import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="Tennis_Jordi",
        user="postgres",
        password="postgres123"
    )

    print("✅ Conexión correcta")

    cur = conn.cursor()

    # Prueba simple
    cur.execute("SELECT version();")
    version = cur.fetchone()

    print("📦 Versión de PostgreSQL:")
    print(version)

    # Prueba con tu tabla jugadores
    cur.execute("SELECT id, nombre FROM jugadores LIMIT 5;")
    jugadores = cur.fetchall()

    print("🎾 Jugadores:")
    for j in jugadores:
        print(j)

    cur.close()
    conn.close()

except Exception as e:
    print("❌ Error de conexión:")
    print(e)