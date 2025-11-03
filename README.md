# Statement Analyzer Web App

Herramienta para analizar extractos bancarios en PDF, categorizar gastos y visualizarlos en una interfaz web interactiva.

## Estructura del proyecto

```
backend/
├── __init__.py
├── category_keywords.json # Configuración editable de categorías y palabras clave
├── server.py              # API FastAPI para subir PDFs
└── statement_analyzer.py  # Lógica de parsing, categorización y payloads

frontend/
├── app.js                 # Lógica del dashboard y consumo del API
├── index.html             # Layout principal
└── styles.css             # Estilos del dashboard

analyze_statement.py       # Script legacy para análisis local
Septiembre 2025.pdf        # Ejemplo de extracto
```

## Requisitos

- Python 3.10+
- Node no es obligatorio (frontend es estático)
- Dependencias Python: `fastapi`, `uvicorn`, `pdfplumber`, `pandas`

Instalación rápida local:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pdfplumber pandas python-multipart
```

## Ejecutar el backend

```bash
uvicorn backend.server:app --reload
```

El servicio quedará disponible en `http://127.0.0.1:8000`.

## Ejecutar el frontend

Sirve los archivos estáticos desde `frontend/`. Ejemplos:

1. Utilizando VS Code Live Server.
2. Usando Python:
   ```bash
   cd frontend
   python -m http.server 5500
   ```

Abre `http://127.0.0.1:5500/` (o el puerto configurado) en tu navegador.

## Flujo de uso

1. Abre el frontend en el navegador.
2. Carga tu PDF mediante el formulario.
3. El backend procesa el archivo, aplica categorización y devuelve un JSON.
4. El dashboard muestra el total general, lista de categorías y transacciones detalladas.

## Notas

- El análisis se basa en las palabras clave definidas en `backend/category_keywords.json`. Puedes editar este archivo (incluso mientras el servidor está corriendo) para añadir, eliminar o mover transacciones entre categorías. Cada clave es una categoría y su valor es la lista de palabras clave asociadas.
- Los datos no se almacenan en el servidor; todo se procesa en memoria.
- `analyze_statement.py` se mantiene como script standalone por si deseas generar gráficos locales.
