import os
import sys
import base64
import subprocess
import threading
import time

class ClipboardManager:
    """Manages system clipboard operations, such as copying files."""

    @staticmethod
    def copy_file_to_clipboard_async(file_path: str, format_type: str = None, on_success=None, on_error=None):
        """Copies a file to the clipboard in a background thread."""
        def copy_task():
            try:
                # 1. Resolve final path if extension changed during post-processing
                actual_path = file_path

                if format_type and format_type not in file_path:
                    base, _ = os.path.splitext(file_path)
                    possible_path = f"{base}.{format_type}"
                    if os.path.exists(possible_path):
                        actual_path = possible_path

                # Wait briefly for postprocessors/FFmpeg to finish writing or replacing the file
                retries = 10
                while not os.path.exists(actual_path) and retries > 0:
                    time.sleep(0.3)
                    retries -= 1

                if not os.path.exists(actual_path):
                    # Try searching directory for matching title if yt-dlp reported temp format
                    dir_name = os.path.dirname(actual_path)
                    base_name = os.path.splitext(os.path.basename(actual_path))[0]
                    found = False
                    if os.path.isdir(dir_name):
                        for f in os.listdir(dir_name):
                            if os.path.splitext(f)[0] == base_name:
                                actual_path = os.path.join(dir_name, f)
                                found = True
                                break
                    if not found:
                        if on_error:
                            on_error("No se encontró archivo final para portapapeles")
                        return

                # 2. Call PowerShell command using System.Windows.Forms with -STA and -EncodedCommand
                abs_path = os.path.abspath(actual_path)
                escaped_path = abs_path.replace("'", "''")
                ps_script = (
                    "Add-Type -AssemblyName System.Windows.Forms;\n"
                    "$list = New-Object System.Collections.Specialized.StringCollection;\n"
                    f"[void]$list.Add('{escaped_path}');\n"
                    "[System.Windows.Forms.Clipboard]::SetFileDropList($list);\n"
                )
                encoded = base64.b64encode(ps_script.encode('utf-16le')).decode('utf-8')
                cmd = ["powershell", "-NoProfile", "-STA", "-EncodedCommand", encoded]

                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=creationflags
                )
                if res.returncode == 0:
                    if on_success:
                        on_success()
                else:
                    err_msg = res.stderr.strip() or f"Código de salida PowerShell: {res.returncode}"
                    print(f"Error copying to clipboard (PS): {err_msg}")
                    if on_error:
                        on_error(err_msg)
            except Exception as e:
                print(f"Error copying to clipboard: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=copy_task, daemon=True).start()
