# 🎵 Universal Downloader

Aplicación de escritorio moderna y fácil de usar para descargar videos y música de **YouTube**, **Spotify** y más de **1000 sitios** de internet. 

Diseñada para ser sencilla: pegás el enlace, elegís el formato y descargás.

---

## 🚀 Guía de Inicio Rápido (Para todo público)

Seguí estos pasos sencillos para instalar y hacer funcionar el programa en tu computadora.

### Paso 1: Instalar Python
El programa está construido sobre Python. Si no lo tenés instalado:
1. Entrá a [python.org](https://www.python.org/downloads/) y descargá la última versión para Windows.
2. **IMPORTANTE:** Al abrir el instalador, asegurate de marcar la casilla que dice **"Add Python to PATH"** (o "Agregar Python al PATH") abajo del todo antes de darle a instalar. Si no marcás esto, el programa no va a funcionar.

### Paso 2: Instalar FFmpeg (Necesario para convertir audios y videos)
FFmpeg es un motor interno que usa el programa para procesar y unir los archivos de audio y video.
* **En Windows (Sencillo):**
  1. Abrí el menú inicio de tu computadora, escribí `Terminal` o `PowerShell` y abrilo.
  2. Copiá y pegá el siguiente comando y apretá Enter:
     ```powershell
     winget install ffmpeg
     ```
  3. Cerrá la ventana cuando termine.

### Paso 3: Descargar y Preparar el Programa
1. Descargá este proyecto a tu computadora (haciendo clic en el botón verde **Code** -> **Download ZIP** arriba a la derecha y descomprimilo en una carpeta).
2. Abrí la carpeta del programa.
3. Buscá el archivo llamado **`start.bat`** y hacé doble clic en él. 
   * *La primera vez que lo abras, instalará automáticamente todas las herramientas necesarias de forma segura y luego abrirá la aplicación.*

---

## 🎮 Cómo Usar la Aplicación

1. **Pegá la URL:** Copiá el enlace de la canción de Spotify o del video de YouTube y pegalo en la barra de texto superior.
2. **Analizá:** Presioná el botón **Analizar**. El programa cambiará de color según la plataforma y buscará el archivo automáticamente.
3. **Elegí tu formato y calidad:** 
   * Seleccioná **Video** (si querés guardarlo con imagen en calidad 1080p, 720p, etc.).
   * Seleccioná **Audio** (si solo querés la música en formato MP3 o similar).
4. **Elegí dónde guardarlo:** Hacé clic en **Examinar** para elegir en qué carpeta de tu computadora querés que se guarde la descarga.
5. **Descargá:** Presioná **Descargar**. Verás el progreso en la barra inferior.

---

## ⚙️ Características Técnicas (Para Desarrolladores)

El proyecto cuenta con una arquitectura desacoplada basada en componentes independientes de GUI y un controlador de descargas asíncrono para evitar el bloqueo del hilo de interfaz gráfica de CustomTkinter.

```
downloader/
├── main.py                 # Punto de entrada de la aplicación
├── requirements.txt        # Librerías de Python requeridas
├── start.bat               # Script automatizado de instalación y arranque rápido
└── src/
    ├── app.py             # Ventana principal (Ensamblador de UI)
    ├── config.py          # Manejo de opciones guardadas del usuario (.json)
    ├── dependency_checker.py # Verificador del entorno de ejecución (ffmpeg, yt-dlp)
    ├── video_downloader.py    # Lógica de descarga nativa de videos
    ├── spotify_downloader.py  # Lógica de conversión de enlaces Spotify a YouTube
    └── gui/               # Componentes aislados de la interfaz
        ├── colors.py          # Paleta visual del proyecto
        ├── controller.py      # Controlador de hilos asíncronos y reproductor
        └── components/        # Sub-paneles interactivos de la aplicación
```

---

## 📜 Licencia
Este proyecto es para uso educativo y personal. Asegurate de cumplir con las políticas y leyes de copyright de tu país.
