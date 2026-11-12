# Universal Downloader

Aplicación de escritorio en Python y CustomTkinter para buscar contenido en YouTube y descargar audio o video con yt-dlp. La compatibilidad con otros sitios depende de los extractores de yt-dlp y del acceso disponible a cada recurso.

## Inicio en Windows

1. Instala Python con Tkinter y activa **Add Python to PATH**.
2. Descarga o clona este repositorio.
3. Ejecuta `start.bat`. Crea `venv`, instala `requirements.txt` y abre la aplicación.
4. Si falta FFmpeg, utiliza el diálogo de dependencias para instalarlo en `bin/`, o instala FFmpeg y FFprobe en el PATH.

El instalador integrado de FFmpeg está destinado a Windows y necesita conexión a Internet. El entorno existente del proyecto utiliza Python 3.14; la compatibilidad de otras versiones depende de las dependencias instaladas. No hay una matriz de versiones certificada.

### Instalación manual y diagnóstico

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

Ejecuta el último comando desde la raíz del proyecto para ver los errores en consola. `start.bat` inicia la aplicación con `pythonw.exe`, que no muestra una consola.

La reproducción de avances de audio usa **pygame**, una dependencia opcional:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-preview.txt
```

Si pygame no tiene una distribución compatible con tu versión de Python, puedes mantener las descargas sin esa función. La vista previa de video usa OpenCV y Pillow; el audio del reproductor depende de que pygame pueda abrir el archivo.

## Uso

1. Pega una URL o escribe una búsqueda y pulsa **Analizar**.
2. Si aparece una lista de resultados, selecciona el contenido.
3. Elige audio o video, formato, calidad y carpeta de destino.
4. Opcionalmente activa recorte, video sin audio o copia al portapapeles.
5. Pulsa **Descargar**. La conversión con FFmpeg puede continuar después de terminar la transferencia.

Para listas compatibles, la interfaz permite elegir un elemento o la lista completa. El descargador de video/audio omite contenido de más de **30 minutos**; ese filtro no se aplica al flujo de Spotify.

### Qué hace el soporte de Spotify

Lee metadatos de la página pública de inserción de Spotify y busca una coincidencia en YouTube. Si no encuentra el nombre, debes introducirlo manualmente. **No descarga el audio original de Spotify**. Un enlace de álbum o lista se usa para obtener texto de búsqueda; no implementa la descarga completa de todas sus canciones.

## Datos y dependencias

| Elemento | Ubicación o función |
| --- | --- |
| Preferencias | `~/.universal_downloader/config.json` |
| FFmpeg y FFprobe locales | `bin/`, junto a `main.py`; también se admite PATH |
| Avances temporales | `.audio_cache/` y `.video_cache/` en el directorio de ejecución |
| Motor de descargas | yt-dlp |
| Interfaz | CustomTkinter y Tkinter |
| Imágenes y video | Pillow y OpenCV |
| Metadatos de Spotify | requests |
| Reproducción opcional | pygame |

Las preferencias se guardan mediante un archivo temporal y sustitución atómica para reducir el riesgo de corrupción. La opción de cookies del navegador se comparte entre descargas y avances. Usa esa opción solo si el contenido requiere tu sesión.

## Desarrollo

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m compileall -q src main.py tests
```

Las pruebas son locales y simulan yt-dlp, errores de FFmpeg y callbacks; no descargan archivos de Internet ni sustituyen una prueba manual de la interfaz.

- [Arquitectura y decisiones](docs/ARCHITECTURE.md)
- [Revisión y limitaciones](docs/REVIEW.md)
- [Guía de contribución](CONTRIBUTING.md)

## Solución de problemas

| Síntoma | Comprobación |
| --- | --- |
| La ventana se cierra al abrir | Ejecuta `main.py` desde consola y revisa el error |
| Falla la conversión o unión | Comprueba `ffmpeg -version` y `ffprobe -version`, o reinstala los binarios locales |
| Spotify no encuentra el nombre | Introduce canción y artista manualmente; los metadatos públicos pueden cambiar |
| Un sitio rechaza el acceso | Actualiza yt-dlp desde el diálogo, comprueba la URL y, si corresponde, las cookies |
| No funciona el avance de audio | Instala pygame y comprueba que hay un dispositivo de audio disponible |
| No se genera un archivo | Comprueba el límite de duración, el acceso al contenido y los mensajes de yt-dlp |

## Licencia

El repositorio no incluye un archivo `LICENSE` con una licencia de software explícita. El uso previsto es educativo y personal; descarga contenido para el que tengas autorización.
