#!/bin/bash
# Reemplazamos python3 por 'python' para mayor compatibilidad de entorno en Render
# Además, cambiamos el comando de inicio para que Flask lo maneje directamente.
exec gunicorn --bind 0.0.0.0:$PORT servidor_final:app
