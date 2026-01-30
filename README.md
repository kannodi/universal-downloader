# 🎵 Universal Downloader

Aplicación de escritorio moderna para descargar videos y música de **YouTube**, **Spotify** y más de **1000 sitios** compatibles con yt-dlp.

![Theme](https://img.shields.io/badge/Theme-Dark-1a1a1a)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Características

- 🎬 **Descarga videos** en múltiples calidades (1080p, 720p, 480p, etc.)
- 🎵 **Descarga audio** en MP3, M4A, FLAC, WAV y más
- 🎧 **Spotify** - Detecta automáticamente la canción y descarga vía YouTube
- 🌐 **+1000 sitios** compatibles vía yt-dlp
- 📊 **Vista previa de calidades** disponibles antes de descargar
- 💾 **Recuerda tu última carpeta** de descarga
- 🔄 **Verificación automática** de dependencias al iniciar
- 🌙 **Interfaz oscura** moderna con CustomTkinter

## 📋 Requisitos

- Python 3.10 o superior
- FFmpeg instalado y en PATH

### Instalar FFmpeg

**Windows (con Chocolatey):**
```bash
choco install ffmpeg
```

**Windows (manual):**
1. Descarga desde [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extrae y añade la carpeta `bin` a tu PATH

## 🚀 Instalación

1. **Clona o descarga** este repositorio

2. **Crea un entorno virtual** (recomendado):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Instala las dependencias**:
```bash
pip install -r requirements.txt
```

## 🎮 Uso

1. **Ejecuta la aplicación**:
```bash
python main.py
```

2. **Pega una URL** de YouTube, Spotify u otro sitio compatible

3. **Haz clic en "Analizar"** para ver las calidades disponibles

4. **Selecciona** el tipo (video/audio), calidad y formato

5. **Elige la carpeta** de destino

6. **Haz clic en "Descargar"**

## 📁 Estructura del Proyecto

```
downloader/
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias Python
├── README.md              # Este archivo
└── src/
    ├── __init__.py
    ├── app.py             # Aplicación principal (GUI)
    ├── config.py          # Gestión de configuración
    ├── dependency_checker.py  # Verificación de dependencias
    ├── video_downloader.py    # Descargador yt-dlp
    └── spotify_downloader.py  # Descargador Spotify
```

## ⚙️ Configuración

La aplicación guarda automáticamente:
- Última carpeta de descarga seleccionada
- Preferencias de formato por defecto

Los archivos de configuración se guardan en:
```
~/.universal_downloader/config.json
```

## 🔧 Solución de Problemas

### FFmpeg no encontrado
Asegúrate de que FFmpeg está instalado y en tu PATH:
```bash
ffmpeg -version
```

### Error al descargar de Spotify
- La app detecta automáticamente el nombre de la canción desde la URL de Spotify
- Luego busca y descarga el audio desde YouTube usando yt-dlp
- Si no detecta el nombre, puedes ingresarlo manualmente
- Opcionalmente, puedes configurar credenciales de Spotify API en ⚙️ Configuración

### Actualizar herramientas
La aplicación te permite actualizar yt-dlp desde el diálogo de dependencias al inicio.

## 📜 Licencia

Este proyecto es para uso educativo y personal. Asegúrate de cumplir con los términos de servicio de cada plataforma y las leyes de copyright de tu país.

---

Hecho con ❤️ usando Python, CustomTkinter y yt-dlp
