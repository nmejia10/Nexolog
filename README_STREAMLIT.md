# NexoLog - Dashboard Streamlit (DATA1002)

Este paquete incluye:

- `app.py`: aplicación Streamlit con filtros, indicadores, gráficos y tabla interactiva.
- `NexoLog_envios.csv`: 3.200 envíos sintéticos que alimentan el dashboard.
- `NexoLog_centros.csv`: catálogo complementario de centros para el taller (no se necesita para los indicadores de la app).
- `requirements.txt`: dependencias para ejecutar localmente o desplegar en Streamlit Community Cloud.

## Ejecutar en computador

En la carpeta que contiene estos archivos:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicar en Streamlit Community Cloud

1. Crea un repositorio en GitHub y sube `app.py`, `NexoLog_envios.csv` y `requirements.txt` a la raíz.
2. Entra a `https://share.streamlit.io/` e inicia sesión.
3. Selecciona **Create app** y el repositorio, rama y archivo `app.py`.
4. Publica y comparte la dirección `.streamlit.app`.

Se trata de datos inventados para fines educativos. Ninguna variable demuestra por sí sola una relación causal.
