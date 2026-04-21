# 🎾 App Tenis Jordi

Aplicación web para gestionar jugadores, torneos, partidos y sets de tenis.

Proyecto en desarrollo paso a paso para aprender backend, bases de datos y desarrollo web.

---

## 🚀 Tecnologías utilizadas

* 🐍 Python
* ⚡ FastAPI
* 🐘 PostgreSQL
* 🎨 HTML (templates con Jinja2)

---

## 📂 Estructura del proyecto

```
app_tennis/
│
├── app/
│   ├── main.py
│   ├── database.py
│   └── templates/
│       ├── index.html
│       ├── jugadores.html
│       ├── torneos.html
│       ├── partidos.html
│       └── sets.html
│
├── run.bat
├── requirements.txt
├── test_db.py
├── .gitignore
└── README.md
```

---

## ▶️ Cómo ejecutar el proyecto

1. Clonar el repositorio:

```
git clone https://github.com/jordi4949/app_tennis.git
```

2. Entrar en la carpeta:

```
cd app_tennis
```

3. Crear y activar entorno virtual:

```
python -m venv venv
venv\Scripts\activate
```

4. Instalar dependencias:

```
pip install -r requirements.txt
```

5. Crear archivo `.env` con tus credenciales:

```
DB_HOST=localhost
DB_NAME=Tennis_Jordi
DB_USER=postgres
DB_PASSWORD=tu_password
DB_PORT=5432
```

6. Ejecutar la aplicación:

```
uvicorn app.main:app --reload
```

7. Abrir en navegador:

👉 http://127.0.0.1:8000

---

## 🔒 Seguridad

Las credenciales de la base de datos NO están en el código.

Se utilizan variables de entorno mediante archivo `.env` (incluido en `.gitignore`).

---

## 📌 Estado del proyecto

✔ Gestión de jugadores
✔ Gestión de torneos
✔ Gestión de partidos (en progreso)
✔ Gestión de sets

---

## 🚧 Próximos pasos

* ✏️ Editar y borrar registros
* 📊 Estadísticas de jugadores
* 📱 Versión accesible desde móvil
* 🎤 Entrada por voz
* 📄 OCR para importar resultados
* 🤖 Integración con IA local

---

## 👨‍💻 Autor

Proyecto creado por Jordi como aprendizaje y desarrollo progresivo en programación y nuevas tecnologías.

---
