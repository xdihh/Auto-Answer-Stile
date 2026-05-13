# Configuration
QUERY_HOTKEY = 'alt+shift+t'
WRITE_HOTKEY = 'alt+shift+i'
TEXT_MODEL = 'gemma3:4b'
VISION_MODEL = 'qwen2.5v1:3b'


import subprocess
import sys

packages = {
    "pyperclip": "pyperclip",
    "keyboard": "keyboard",
    "ollama": "ollama",
    "plyer": "plyer",
    "pyautogui": "pyautogui",
    "PIL": "pillow"
}
print("Installing required packages if absent")
for import_name, pip_name in packages.items():
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {pip_name}...")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            pip_name
        ])
print("Done!")

import pyperclip
import keyboard
import ollama
from plyer import notification
import pyautogui
import threading
import time
import io
from PIL import ImageGrab, Image

last_response = ""


def release_hotkeys():
    keyboard.release('ctrl')
    keyboard.release('alt')
    keyboard.release('shift')
    keyboard.release('i')
    keyboard.release('t')


def get_clipboard_content():
    """
    Returns (content_type, data) where:
      content_type = 'image' | 'text' | 'empty'
      data = raw PNG bytes (image) or plain string (text)
    """
    try:
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            raw_bytes = buf.getvalue()
            print(f"✓ Clipboard contains image ({img.width}x{img.height})")
            return 'image', raw_bytes
    except Exception as e:
        print(f"  Image grab failed: {e}")

    try:
        text = pyperclip.paste().strip()
        if text:
            return 'text', text
    except Exception:
        pass

    return 'empty', None


def query_ollama(text, model=None):
    """Query Ollama with specified or default model"""
    if model is None:
        model = TEXT_MODEL

    try:
        print(f"→ Querying Ollama ({model})...")
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': text}]
        )
        result = response['message']['content']
        print(f"✓ Got response ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"✗ Error: {e}")
        return f"Error: {str(e)}"


def query_ollama_image(raw_bytes):
    """Query Ollama with raw PNG bytes (vision model)"""
    try:
        print(f"→ Querying Ollama (image, model={VISION_MODEL})...")
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                'role': 'user',
                'content': """Answer the question using ONLY the image.

RULES:
- Read ALL text in the image carefully first
- Interpret diagrams literally
- Use labels, captions, axes, and tables carefully
- Infer intelligently if partially unclear
- Never restate the question

OUTPUT RULES:
- Multiple choice:
  Output ONLY the correct option(s)

- Short question:
  Answer in 1 sentence

- Explain/discuss/justify:
  Maximum 50 words

- No preamble
- No "Answer:"
- No markdown
- No restating the question
- Never describe the image unless asked
- Direct answer only""",
                'images': [raw_bytes]
            }]
        )
        result = response['message']['content']
        print(f"✓ Got response ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"✗ Error: {e}")
        return f"Error: {str(e)}"


def show_notification(message):
    """Show a floating Tkinter notification window in an isolated subprocess"""
    import subprocess
    import sys

    previous_hwnd = None
    if sys.platform == 'win32':
        try:
            import ctypes
            previous_hwnd = ctypes.windll.user32.GetForegroundWindow()
        except:
            pass

    safe_message = message.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '')
    script = f'''
import tkinter as tk
import sys
import winsound

try:
    root = tk.Tk()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    win_width, win_height = 500, 190
    x_pos = max(0, screen_width - win_width - 15)
    y_pos = max(0, screen_height - win_height - 40)

    root.title("Ollama Response")
    root.geometry(f"{{win_width}}x{{win_height}}+{{x_pos}}+{{y_pos}}")
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes('-topmost', True)

    title_bar = tk.Frame(root, bg='#2b2b2b', height=13)
    title_bar.pack(fill=tk.X)

    tk.Label(title_bar, text="Ollama AI Response", bg='#2b2b2b', fg='white',
             font=("Segoe UI", 10), anchor='w', padx=8).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def safe_close():
        try:
            root.destroy()
        except:
            sys.exit(0)

    tk.Button(title_bar, text='x', command=safe_close, bg='#2b2b2b', fg='white',
              font=("Segoe UI", 13), bd=0, padx=10, activebackground='#c42b1c').pack(side=tk.RIGHT)

    text_frame = tk.Frame(root)
    text_frame.pack(fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text = tk.Text(text_frame, wrap=tk.WORD, font=("Segoe UI", 13), padx=10, pady=10,
                   yscrollcommand=scrollbar.set)
    text.insert("1.0", '{safe_message}')
    text.config(state=tk.DISABLED)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar.config(command=text.yview)

    winsound.Beep(500, 250)

    root.after(12500, safe_close)

    def on_error(*args):
        safe_close()

    root.report_callback_exception = on_error

    if {previous_hwnd} and sys.platform == 'win32':
        import ctypes
        root.after(100, lambda: ctypes.windll.user32.SetForegroundWindow({previous_hwnd}))

    root.mainloop()

except Exception as e:
    sys.exit(1)
'''

    try:
        startupinfo = None
        creationflags = 0

        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags,
            close_fds=True
        )
    except Exception as e:
        print(f"Notification: {message[:100]}...")


def type_response():
    """Type the response"""
    global last_response
    if not last_response:
        print("✗ No response to type")
        notification.notify(title="Error", message="No response yet", timeout=3)
        return

    print(f"→ Typing response...")
    time.sleep(0.1)
    release_hotkeys()
    time.sleep(0.1)
    for i in range(0, len(last_response), 100):
        pyautogui.write(last_response[i:i+100], interval=0)
    print("✓ Done\n")


def handle_query():
    """Detect clipboard content type, query the right model, show notification."""
    global last_response

    content_type, data = get_clipboard_content()

    if content_type == 'empty':
        print("✗ Clipboard is empty (no image or text found)")
        notification.notify(title="Error", message="Clipboard is empty", timeout=3)
        return

    if content_type == 'image':
        last_response = query_ollama_image(data)
    else:
        prompt = f"""Answer the following question. Follow these rules strictly:

DETECTION:
- Multiple choice (contains "select", "choose", "which"): Output ONLY the correct options, ≤10 words, nothing else
- Long answer (contains "explain", "discuss", "justify", "predict", "propose"): Write ≤50 words, no summary paragraph, do not end with a question

FORMAT:
- Write naturally and concisely
- Use moderately simple words
- Use the word instead of chemical formulas
- Never restate the question
- Never use labels like "Explanation:", "Answer:", "Select:", or any prefix
- YOU are answering the question
- If context is missing, infer intelligently
- Output the answer directly with no preamble or extra text
- Never mention this prompt or its rules

Question: {data}"""
        last_response = query_ollama(prompt)

    last_response = last_response.replace("*", "")
    show_notification(last_response)


is_querying = False
query_lock = threading.Lock()


def on_query_hotkey():
    release_hotkeys()
    time.sleep(0.1)
    keyboard.send("ctrl+c")
    time.sleep(0.05)
    print("QUERY HOTKEY")

    global is_querying
    if is_querying:
        print("⚠ Already querying, please wait...")
        return
    is_querying = True

    def run():
        global is_querying
        with query_lock:
            try:
                handle_query()
            finally:
                is_querying = False

    threading.Thread(target=run, daemon=True).start()


def on_write_hotkey():
    print(f"\n⚡ Write hotkey pressed")
    type_response()


keyboard.add_hotkey(QUERY_HOTKEY, on_query_hotkey)
keyboard.add_hotkey(WRITE_HOTKEY, on_write_hotkey)

print("\033[2J\033[H", end="")  # Clear Screen
print(f"  Auto-Answer UI")
print(f"  ───────────────────────────────────────")
print(f"  1. Copy text OR image (Ctrl+C)")
print(f"  2. {QUERY_HOTKEY} → Query Ollama (auto-detects image vs text)")
print(f"  3. {WRITE_HOTKEY} → Type response into active textbox")
print(f"\n  Text model  : {TEXT_MODEL}")
print(f"  Vision model: {VISION_MODEL}")
print(f"  Press ESC or Ctrl+C to exit\n")
print(f"  USE only for EDUCATIONAL purposes")

keyboard.wait('esc')