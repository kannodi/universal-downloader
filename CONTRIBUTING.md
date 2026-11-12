# Desarrollo y contribución

1. Crea una rama para el cambio y conserva las modificaciones locales anteriores.
2. Instala `requirements.txt` en un entorno virtual. Usa `requirements-preview.txt` solo si necesitas reproducción de audio.
3. Mantén las operaciones de red y conversiones fuera del hilo de interfaz. Lee las opciones Tk antes de lanzar un trabajador y programa los cambios visuales con `after`.
4. Usa `src.runtime.ydl_options` para compartir cookies y FFmpeg. Las funciones de clasificación de entrada pertenecen a `src.urls`.
5. Añade pruebas de regresión para errores de estado, persistencia y contratos con yt-dlp. Simula la red y los procesos externos.
6. Ejecuta `python -m unittest discover -s tests -v`, `python -m compileall -q src main.py tests` y `git diff --check`.
7. Si cambias widgets o reproducción, prueba manualmente análisis, cambio de formato, descarga, cancelación y cierre durante una operación.

No incluyas entornos virtuales, binarios, cachés, cookies ni preferencias personales en commits. Si cambias una función visible para el usuario, actualiza el README y documenta sus límites.
