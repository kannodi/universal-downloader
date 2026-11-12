# Revisión de arquitectura y documentación

Revisión del árbol local, incluidos los cambios sin commit existentes. Se conservaron esos cambios al preparar la revisión.

## Problemas corregidos

| Hallazgo | Corrección |
| --- | --- |
| Spotify referenciaba `os` sin importarlo | Se sustituyó la duplicación por opciones comunes de runtime |
| Los callbacks diferidos capturaban una excepción fuera de su ámbito | Captura del texto como argumento de la función diferida |
| Descargas podían devolver éxito sin archivo final o con error de yt-dlp | Verificación del código de salida y del post hook final |
| Los posprocesadores ocultaban fallos de conversión y de eliminación de audio | Propagación de `PostProcessingError` |
| Se desactivaba la comprobación de certificados | Restauración del comportamiento TLS predeterminado |
| Dominios se detectaban por subcadenas de toda la entrada | Clasificación por límites del hostname |
| JSON válido con estructura incorrecta rompía las preferencias | Validación del objeto y combinación con valores predeterminados |
| Una escritura interrumpida podía truncar preferencias | Temporal y reemplazo atómico |
| FFmpeg dependía del directorio desde donde se iniciaba Python | Resolución a partir de la raíz del código |
| Instalación de FFmpeg compartía un ZIP temporal y no verificaba ambos binarios | Directorio temporal único, limpieza y verificación de miembros |
| El hilo de descarga leía variables Tk directamente | Captura de opciones antes de arrancar el hilo |
| Cambiar a audio consultaba un atributo eliminado del controlador | Uso de `preview_player.has_file` |
| El reproductor conservaba el estado activo al acabar | Restablecimiento al detectar fin natural |
| Los tests estaban excluidos de Git | Eliminación de esa regla y adición de regresiones |
| README sobrestimaba soporte y no explicaba dependencias opcionales | Documentación de comportamiento, requisitos y límites reales |

## Pendientes conocidos

- El cierre no espera a todos los hilos; un callback puede llegar después de destruir la ventana. La limpieza de cachés también puede competir con una descarga de avance.
- Los avances de video y audio pueden compartir el reproductor global de pygame y aún no tienen exclusión mutua ni cancelación propia.
- Las cachés siguen dependiendo del directorio de ejecución. No tienen límite de tamaño durante la sesión.
- El recorte duplica el análisis de tiempos y trata algunos valores incorrectos como cero. Conviene validarlo en una solicitud independiente.
- La actualización integrada modifica el entorno con pip y requiere reinicio para asegurar que se cargue la versión nueva.
- La instalación de FFmpeg descarga un ZIP por HTTPS sin verificación adicional de checksum. No hay versiones fijadas ni lockfile de dependencias.
- No hay integración continua ni matriz de sistemas operativos/Python. Portapapeles e instalador están orientados a Windows.
- La reproducción de audio es opcional y no está instalada en el entorno revisado. Requiere comprobación manual con pygame y un dispositivo de audio.
- No se verificaron descargas reales, cambios de páginas de terceros ni el comportamiento visual de la GUI.

## Verificación reproducible

Desde la raíz: `python -m unittest discover -s tests -v` y `python -m compileall -q src main.py tests`.

Las pruebas cubren preferencias dañadas, persistencia ante fallos, detección de hostnames, opciones compartidas, rutas de ejecutables, resultados fallidos o vacíos, post hooks finales, excepciones de FFmpeg, callbacks diferidos y bloqueo de descargas duplicadas. Simulan los servicios externos y no certifican compatibilidad con sitios reales.

Resultado de esta revisión: **16 pruebas aprobadas**, compilación de `src`, `main.py` y `tests` sin errores, importación de `src.app` correcta y `git diff --check` sin problemas de espacios. Se utilizó el Python 3.14.7 del entorno virtual existente, con yt-dlp 2026.07.04. No se inició la GUI ni se hicieron descargas reales.

Verificación previa a publicación: 16 pruebas aprobadas, compilación e importación correctas con Python 3.14.7 y yt-dlp 2026.10.26; `pip check` no detectó conflictos de dependencias.
