# =================================================================================
# 1. IMPORT LIBRARIES
# =================================================================================
import pygame
from datetime import datetime
import os
import math
import random
import json
import uuid
import threading
import time

# --- Weather HTTP ---
try:
    import requests
except ImportError:
    requests = None

# --- Transparent drag (Windows only) ---
try:
    import win32api, win32con, win32gui
except ImportError:
    win32api = None
    print("Warning: 'pywin32' not found. Window transparency and dragging will be disabled.")

# --- Native file picker for custom background / sound ---
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None
    filedialog = None
    print("Warning: 'tkinter' not available. File picker will be disabled.")


# =================================================================================
# 2. INITIALIZE & SETUP CORE APP VARIABLES
# =================================================================================
pygame.init()
WIDTH, HEIGHT = 600, 600
CORNER_RADIUS = 25
CONFIG_FILE = 'config.json'
TODO_FILE = 'todo.json'

# --- Paths ---
script_dir = os.path.dirname(__file__)
assets_dir = os.path.join(script_dir, '..', 'assets')
fonts_dir = os.path.join(assets_dir, 'fonts')
TRANSPARENT_COLOR = (0, 255, 0)

# --- Top bar buttons ---
settings_button_rect = pygame.Rect(10, 10, 30, 30)
weather_button_rect  = pygame.Rect(50, 10, 30, 30)
pomodoro_button_rect = pygame.Rect(90, 10, 30, 30)
close_button_rect    = pygame.Rect(WIDTH - 40, 10, 30, 30)

# =================================================================================
# 3. CREATE THE CUSTOM WINDOW
# =================================================================================
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Trife Living Clock")

hwnd = None
if win32api:
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(
        hwnd,
        win32con.GWL_EXSTYLE,
        win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED
    )
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0, win32con.LWA_COLORKEY)


# =================================================================================
# 4. LOAD ASSETS & DEFINE THEMES
# =================================================================================
try:
    chibi_frames = {
        'normal': [
            pygame.image.load(os.path.join(assets_dir, 'open.png')).convert_alpha(),
            pygame.image.load(os.path.join(assets_dir, 'half.png')).convert_alpha(),
            pygame.image.load(os.path.join(assets_dir, 'off.png')).convert_alpha()
        ],
        'blush': [
            pygame.image.load(os.path.join(assets_dir, 'blushOpen.png')).convert_alpha(),
            pygame.image.load(os.path.join(assets_dir, 'blushhalf.png')).convert_alpha(),
            pygame.image.load(os.path.join(assets_dir, 'blushClose.png')).convert_alpha()
        ]
    }

    _temp_raw_backgrounds = {}
    _temp_raw_backgrounds['bg1'] = pygame.transform.scale(
        pygame.image.load(os.path.join(assets_dir, 'bg.jpg')).convert_alpha(), (WIDTH, HEIGHT)
    )
    try:
        _temp_raw_backgrounds['bg2'] = pygame.transform.scale(
            pygame.image.load(os.path.join(assets_dir, 'bg_2.jpeg')).convert_alpha(), (WIDTH, HEIGHT)
        )
    except FileNotFoundError:
        print("Warning: 'bg_2.jpeg' not found. Using 'bg1.jpg' as a fallback.")
    raw_backgrounds = _temp_raw_backgrounds

    # ICONS (customizable): gear.png (required), weather.png (optional), pomodoro.png (optional)
    settings_icon = pygame.transform.scale(
        pygame.image.load(os.path.join(assets_dir, 'gear.png')).convert_alpha(), (30, 30)
    )
    weather_png = None
    pomodoro_png = None
    try:
        weather_png = pygame.image.load(os.path.join(assets_dir, 'weather.png')).convert_alpha()
        weather_png = pygame.transform.smoothscale(weather_png, (30, 30))
    except Exception:
        weather_png = None
    try:
        pomodoro_png = pygame.image.load(os.path.join(assets_dir, 'pomodoro.png')).convert_alpha()
        pomodoro_png = pygame.transform.smoothscale(pomodoro_png, (30, 30))
    except Exception:
        pomodoro_png = None

    # To-Do icons (placeholder)
    add_task_icon = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(add_task_icon, (100, 255, 100), (10, 10), 9)
    pygame.draw.line(add_task_icon, (0, 0, 0), (10, 5), (10, 15), 2)
    pygame.draw.line(add_task_icon, (0, 0, 0), (5, 10), (15, 10), 2)

    delete_task_icon = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(delete_task_icon, (255, 100, 100), (10, 10), 9)
    pygame.draw.line(delete_task_icon, (0, 0, 0), (5, 5), (15, 15), 2)
    pygame.draw.line(delete_task_icon, (0, 0, 0), (5, 15), (15, 5), 2)

    # Fonts (keep paths to compute dynamic sizes)
    FONT_BOLD_PATH = os.path.join(fonts_dir, 'Doto_Rounded-Bold.ttf')
    FONT_REG_PATH  = os.path.join(fonts_dir, 'Doto_Rounded-Regular.ttf')

    font_bold = pygame.font.Font(FONT_BOLD_PATH, 150)  # main clock
    font_regular = pygame.font.Font(FONT_REG_PATH, 36)
    font_small = pygame.font.Font(FONT_REG_PATH, 24)
    font_tiny = pygame.font.Font(FONT_REG_PATH, 18)
    font_weather_big  = pygame.font.Font(FONT_BOLD_PATH, 96)
    font_pomo_big     = pygame.font.Font(FONT_BOLD_PATH, 96)

except Exception as e:
    print(f"FATAL ERROR: Could not load essential assets: {e}. Please check your assets folder and font files.")
    exit()

THEMES = {"Purple": (189, 147, 249), "Cyan": (136, 192, 208), "Orange": (255, 184, 108)}
DIGIT_COLORS = {"White": (255, 255, 255), "Black": (0, 0, 0), "Gray": (200, 200, 200)}


# =================================================================================
# 5. SETTINGS & PERSISTENCE
# =================================================================================
current_background_key = 'bg1'
current_theme_color = THEMES["Purple"]
current_digit_color = DIGIT_COLORS["White"]
custom_background_path = None
tasks = []

weather_config = {"api_key": "", "city": "Dhaka", "units": "metric", "refresh_minutes": 15}
pomodoro_config = {"focus_minutes": 25, "short_break_minutes": 5, "long_break_minutes": 15,
                   "sessions_before_long": 4, "auto_advance": True}
# volume control uses gain_percent 0..200 (100 = normal)
sound_config = {"enabled": True, "path": None, "gain_percent": 100}

def save_settings():
    theme_name = [name for name, color in THEMES.items() if color == current_theme_color][0]
    digit_color_name = [name for name, color in DIGIT_COLORS.items() if color == current_digit_color][0]
    with open(CONFIG_FILE, 'w') as f:
        json.dump({
            'background': current_background_key,
            'theme_name': theme_name,
            'digit_color_name': digit_color_name,
            'weather': weather_config,
            'pomodoro': pomodoro_config,
            'sound': sound_config,
            'custom_background_path': custom_background_path
        }, f, indent=4)

def load_settings():
    global current_theme_color, current_background_key, current_digit_color
    global custom_background_path, weather_config, pomodoro_config, sound_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)

        custom_background_path = settings.get("custom_background_path") or None
        if custom_background_path and os.path.exists(custom_background_path):
            try:
                img = pygame.image.load(custom_background_path).convert_alpha()
                img = pygame.transform.scale(img, (WIDTH, HEIGHT))
                temp = img.copy(); temp.blit(overlay, (0, 0))
                raw_backgrounds["custom"] = img
                rounded_backgrounds["custom"] = apply_rounded_corners(temp, CORNER_RADIUS)
            except Exception as e:
                print(f"Warning: failed to load custom background at startup: {e}")
                custom_background_path = None

        loaded_bg_key = settings.get('background', current_background_key)
        current_background_key = loaded_bg_key if loaded_bg_key in raw_backgrounds else 'bg1'

        current_theme_color = THEMES.get(settings.get('theme_name', "Purple"), THEMES["Purple"])
        current_digit_color = DIGIT_COLORS.get(settings.get('digit_color_name', "White"), DIGIT_COLORS["White"])

        wc = settings.get("weather", {})
        weather_config.update({
            "api_key": wc.get("api_key", weather_config["api_key"]),
            "city": wc.get("city", weather_config["city"]),
            "units": wc.get("units", weather_config["units"]),
            "refresh_minutes": int(wc.get("refresh_minutes", weather_config["refresh_minutes"])),
        })

        pc = settings.get("pomodoro", {})
        pomodoro_config.update({
            "focus_minutes": int(pc.get("focus_minutes", pomodoro_config["focus_minutes"])),
            "short_break_minutes": int(pc.get("short_break_minutes", pomodoro_config["short_break_minutes"])),
            "long_break_minutes": int(pc.get("long_break_minutes", pomodoro_config["long_break_minutes"])),
            "sessions_before_long": int(pc.get("sessions_before_long", pomodoro_config["sessions_before_long"])),
            "auto_advance": bool(pc.get("auto_advance", pomodoro_config["auto_advance"])),
        })

        sc = settings.get("sound", {})
        if "gain_percent" not in sc and "volume" in sc:
            sc["gain_percent"] = int(float(sc["volume"]) * 100)
        sound_config.update({
            "enabled": bool(sc.get("enabled", sound_config["enabled"])),
            "path": sc.get("path", sound_config["path"]),
            "gain_percent": int(sc.get("gain_percent", sound_config["gain_percent"]))
        })

    except (FileNotFoundError, json.JSONDecodeError):
        save_settings()

def load_tasks():
    global tasks
    try:
        with open(TODO_FILE, 'r') as f:
            tasks_data = json.load(f)
        tasks = []
        for task in tasks_data:
            if 'id' not in task:
                task['id'] = str(uuid.uuid4())
            else:
                task['id'] = str(task['id'])
            tasks.append(task)
    except (FileNotFoundError, json.JSONDecodeError):
        tasks = []
    tasks.sort(key=lambda t: t['completed'])

def save_tasks():
    with open(TODO_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)


# =================================================================================
# 6. HELPERS & PRE-RENDERING
# =================================================================================
def apply_rounded_corners(image_surface, radius):
    mask = pygame.Surface(image_surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255), (0, 0, *image_surface.get_size()), border_radius=radius)
    rounded_image = image_surface.copy()
    rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return rounded_image

def draw_text_with_shadow(surface, text, font, color, position, shadow_color=(0,0,0)):
    x, y = position
    sh = font.render(text, True, shadow_color); surface.blit(sh, (x+3, y+3))
    tx = font.render(text, True, color); surface.blit(tx, (x, y))

def ease_out_quad(t): return t*(2-t)
def ease_in_out_quad(t): return t*t*2 if t<0.5 else (-2*t*t)+(4*t)-1

overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
overlay.fill((0, 0, 0, 80))
rounded_backgrounds = {}
for key, bg_image in raw_backgrounds.items():
    tmp = bg_image.copy(); tmp.blit(overlay, (0,0))
    rounded_backgrounds[key] = apply_rounded_corners(tmp, CORNER_RADIUS)

# To-Do UI
add_task_button_rect = pygame.Rect(WIDTH - 50, HEIGHT - 50, 30, 30)
task_input_active = False
task_input_text = ""
input_box_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT - 80, 300, 40)
task_rects = {}

# --- Load settings & tasks after helpers (needs overlay above) ---
load_settings()
load_tasks()


# =================================================================================
# 6.5 CUSTOM BACKGROUND PICKER
# =================================================================================
def add_custom_background():
    """Open file dialog for user to choose an image and load it as custom background."""
    global custom_background_path, current_background_key
    if filedialog is None:
        print("Custom background picker is unavailable (tkinter missing).")
        return
    try:
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Choose Background Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")]
        )
    finally:
        try: root.destroy()
        except Exception: pass
    if not file_path: return
    try:
        img = pygame.image.load(file_path).convert_alpha()
        img = pygame.transform.scale(img, (WIDTH, HEIGHT))
        temp_surface = img.copy(); temp_surface.blit(overlay, (0, 0))
        raw_backgrounds["custom"] = img
        rounded_backgrounds["custom"] = apply_rounded_corners(temp_surface, CORNER_RADIUS)
        custom_background_path = os.path.abspath(file_path)
        current_background_key = "custom"
        save_settings()
        print(f"[INFO] Custom background loaded: {custom_background_path}")
    except Exception as e:
        print(f"Error loading custom background: {e}")


# =================================================================================
# 6.6 SOUND MANAGER  (0–200% via overlapping copies when >100)
# =================================================================================
class SoundManager:
    def __init__(self, cfg):
        self.enabled = bool(cfg.get("enabled", True))
        self.path    = cfg.get("path")
        self.gain_percent = int(cfg.get("gain_percent", 100))  # 0..200
        self.sound   = None
        self.mixer_ok = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.mixer_ok = True
        except Exception as e:
            print("Audio init failed:", e)
        self._load_sound()

    def _load_sound(self):
        self.sound = None
        if not (self.mixer_ok and self.path):
            return
        try:
            s = pygame.mixer.Sound(self.path)
            self.sound = s
        except Exception as e:
            print("Failed to load sound:", e)

    def set_path(self, path: str):
        self.path = path
        self._load_sound()

    def set_gain_percent(self, pct: int):
        self.gain_percent = max(0, min(200, int(pct)))

    def play(self):
        if not self.enabled:
            return
        if self.sound:
            base = min(1.0, self.gain_percent / 100.0)
            try:
                self.sound.set_volume(base)
                self.sound.play()
                # Overclock: add overlapping copies for >100%
                extra = max(0, (self.gain_percent - 100) // 50)  # 101–150% → 1 copy, 151–200% → 2 copies
                for _ in range(extra):
                    self.sound.play()
                return
            except Exception as e:
                print("Sound play failed:", e)
        # Fallback simple beep on Windows (not volume-controlled; double-beep if overclocking)
        try:
            import winsound
            winsound.Beep(880, 400)
            if self.gain_percent > 150:
                winsound.Beep(880, 400)
        except Exception:
            pass

sound_manager = SoundManager(sound_config)

def choose_custom_sound():
    """Pick a small audio file (≤15s recommended) for notifications."""
    if filedialog is None:
        print("File picker unavailable (tkinter missing)."); return
    try:
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Choose Notification Sound (≤15s recommended)",
            filetypes=[("Audio Files", "*.wav;*.ogg;*.mp3")]
        )
    finally:
        try: root.destroy()
        except Exception: pass
    if not file_path: return
    abs_path = os.path.abspath(file_path)
    sound_manager.set_path(abs_path)
    sound_config["path"] = abs_path
    save_settings()


# =================================================================================
# 6.7 WEATHER SERVICE
# =================================================================================
class WeatherService:
    def __init__(self, config, on_update=None):
        self.city = config.get("city", "Dhaka")
        self.api_key = config.get("api_key", "")
        self.units = config.get("units", "metric")
        self.refresh_secs = max(60, int(config.get("refresh_minutes", 15)) * 60)
        self._lock = threading.Lock()
        self._last_fetch = 0
        self._snapshot = {"ok": False, "reason": "Not fetched yet."}
        self._running = True
        self._on_update = on_update
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self): self._running = False

    def _loop(self):
        while self._running:
            now = time.time()
            if now - self._last_fetch >= self.refresh_secs or not self._snapshot.get("ok", False):
                self._fetch_once()
            time.sleep(1)

    def _fetch_once(self):
        if requests is None:
            snap = {"ok": False, "reason": "Install 'requests' to enable weather."}
            with self._lock:
                self._snapshot = snap; self._last_fetch = time.time()
            return
        if not self.api_key:
            snap = {"ok": False, "reason": "Set weather.api_key in config.json."}
            with self._lock:
                self._snapshot = snap; self._last_fetch = time.time()
            return
        url = f"http://api.weatherapi.com/v1/forecast.json?key={self.api_key}&q={self.city}&days=3&aqi=no&alerts=yes"
        try:
            r = requests.get(url, timeout=6); r.raise_for_status()
            data = r.json()
            current = data.get("current", {})
            fdays = (data.get("forecast", {}) or {}).get("forecastday", [])[:3]

            metric = (self.units == "metric")
            temp = current.get("temp_c") if metric else current.get("temp_f")
            feels = current.get("feelslike_c") if metric else current.get("feelslike_f")
            wind = current.get("wind_kph") if metric else current.get("wind_mph")
            temp_unit = "°C" if metric else "°F"
            wind_unit = "kph" if metric else "mph"

            today = fdays[0]["day"] if fdays else {}
            pop_today = today.get("daily_chance_of_rain")
            high = today.get("maxtemp_c") if metric else today.get("maxtemp_f")
            low  = today.get("mintemp_c") if metric else today.get("mintemp_f")

            mini = []
            for fd in fdays:
                d = fd.get("date")
                dd = fd.get("day", {})
                mini.append({
                    "date": d,
                    "cond": (dd.get("condition") or {}).get("text", ""),
                    "high": dd.get("maxtemp_c") if metric else dd.get("maxtemp_f"),
                    "low":  dd.get("mintemp_c") if metric else dd.get("mintemp_f"),
                    "pop":  dd.get("daily_chance_of_rain"),
                })

            snapshot = {
                "ok": True,
                "city": (data.get("location") or {}).get("name", self.city),
                "country": (data.get("location") or {}).get("country", ""),
                "temp": temp, "feels": feels, "temp_unit": temp_unit,
                "condition": (current.get("condition") or {}).get("text", ""),
                "humidity": current.get("humidity"),
                "wind": wind, "wind_unit": wind_unit,
                "precip_mm": current.get("precip_mm"),
                "uv": current.get("uv"), "cloud": current.get("cloud"),
                "pop_today": pop_today, "high": high, "low": low,
                "alerts": data.get("alerts", {}), "mini": mini
            }
            with self._lock:
                self._snapshot = snapshot; self._last_fetch = time.time()
            if self._on_update: self._on_update(snapshot)
        except Exception as e:
            with self._lock:
                self._snapshot = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
                self._last_fetch = time.time()

    def get_snapshot(self):
        with self._lock:
            return dict(self._snapshot)

weather_service = WeatherService(weather_config)


# =================================================================================
# 6.8 POMODORO TIMER
# =================================================================================
class PomodoroTimer:
    def __init__(self, cfg, on_session_complete=None):
        self.focus_minutes = int(cfg.get("focus_minutes", 25))
        self.short_break_minutes = int(cfg.get("short_break_minutes", 5))
        self.long_break_minutes  = int(cfg.get("long_break_minutes", 15))
        self.sessions_before_long = int(cfg.get("sessions_before_long", 4))
        self.auto_advance = bool(cfg.get("auto_advance", True))

        self.mode = 'focus'  # 'focus' | 'short_break' | 'long_break'
        self.sessions_completed = 0
        self.running = False
        self.remaining_ms = self._duration_for(self.mode) * 1000
        self._last_tick_ms = pygame.time.get_ticks()

        self.cb_complete = on_session_complete

    def _duration_for(self, mode):
        if mode == 'focus': return self.focus_minutes * 60
        if mode == 'short_break': return self.short_break_minutes * 60
        if mode == 'long_break': return self.long_break_minutes * 60
        return 1500

    def toggle(self):
        self.running = not self.running
        self._last_tick_ms = pygame.time.get_ticks()

    def reset(self):
        self.running = False
        self.remaining_ms = self._duration_for(self.mode) * 1000

    def skip(self):
        self.running = False
        self._advance_mode()
        if self.auto_advance:
            self.running = True
        self._last_tick_ms = pygame.time.get_ticks()

    def _advance_mode(self):
        if self.mode == 'focus':
            self.sessions_completed += 1
            if self.sessions_completed % self.sessions_before_long == 0:
                self.mode = 'long_break'
            else:
                self.mode = 'short_break'
        else:
            self.mode = 'focus'
        self.remaining_ms = self._duration_for(self.mode) * 1000

    def update(self):
        if not self.running:
            self._last_tick_ms = pygame.time.get_ticks()
            return
        now = pygame.time.get_ticks()
        delta = now - self._last_tick_ms
        self._last_tick_ms = now
        self.remaining_ms = max(0, self.remaining_ms - delta)
        if self.remaining_ms == 0:
            prev = self.mode
            self.running = False
            self._advance_mode()
            try:
                if self.cb_complete:
                    self.cb_complete(prev, self.mode)
            finally:
                if self.auto_advance:
                    self.running = True

    def set_auto(self, on): self.auto_advance = bool(on)
    def format_mmss(self):
        total = self.remaining_ms // 1000
        m = total // 60; s = total % 60
        return f"{m:02d}:{s:02d}"
    def progress_ratio(self):
        dur = self._duration_for(self.mode) * 1000
        return 1.0 - (self.remaining_ms / dur) if dur > 0 else 0.0

pomodoro_timer = PomodoroTimer(pomodoro_config, on_session_complete=lambda prev, new: sound_manager.play())


# =================================================================================
# 6.9 UI HELPERS (icons, tooltips, weather & pomodoro views)
# =================================================================================
def draw_weather_icon(surface, rect, color=(255,255,255), accent=(255,255,255)):
    icon = pygame.Surface(rect.size, pygame.SRCALPHA)
    w, h = rect.size
    pygame.draw.circle(icon, color, (int(w*0.35), int(h*0.55)), int(h*0.22))
    pygame.draw.circle(icon, color, (int(w*0.55), int(h*0.50)), int(h*0.27))
    pygame.draw.circle(icon, color, (int(w*0.70), int(h*0.60)), int(h*0.20))
    pygame.draw.rect(icon, color, (int(w*0.25), int(h*0.60), int(w*0.55), int(h*0.18)), border_radius=8)
    for x in (0.35, 0.55, 0.75):
        pygame.draw.line(icon, accent, (int(w*x)-3, int(h*0.82)), (int(w*x), int(h*0.90)), 2)
    surface.blit(icon, rect.topleft)

def draw_tomato_icon(surface, rect):
    icon = pygame.Surface(rect.size, pygame.SRCALPHA)
    w, h = rect.size
    pygame.draw.ellipse(icon, (220, 50, 50), (2, 6, w-4, h-6))
    cx, cy = w//2, int(h*0.25)
    pygame.draw.polygon(icon, (40, 160, 70), [(cx, 0), (cx-6, cy), (cx+6, cy)])
    pygame.draw.polygon(icon, (40, 160, 70), [(cx-6, cy), (cx-12, cy+6), (cx, cy+4)])
    pygame.draw.polygon(icon, (40, 160, 70), [(cx+6, cy), (cx+12, cy+6), (cx, cy+4)])
    surface.blit(icon, rect.topleft)

def draw_tooltip(surface, text, anchor_rect, font, alpha, bg=(30, 32, 40), fg=(255, 255, 255)):
    if alpha <= 0: return
    pad_x, pad_y = 10, 6
    text_surf = font.render(text, True, fg)
    w = text_surf.get_width() + pad_x * 2
    h = text_surf.get_height() + pad_y * 2
    x = max(8, min(anchor_rect.centerx - w // 2, surface.get_width() - w - 8))
    y = anchor_rect.bottom + 8
    tooltip_rect = pygame.Rect(x, y, w, h)
    bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bg_surf, (*bg, int(alpha)), bg_surf.get_rect(), border_radius=8)
    surface.blit(bg_surf, tooltip_rect.topleft)
    surface.blit(text_surf, (tooltip_rect.x + pad_x, tooltip_rect.y + pad_y))

def draw_weather_summary_inline(surface, pos, fonts, theme_color):
    font_small, font_tiny = fonts
    snap = weather_service.get_snapshot()
    x, y = pos
    if not snap.get("ok"):
        txt = snap.get("reason", "Weather loading…")
        surface.blit(font_tiny.render(txt, True, (210,210,210)), (x, y)); return
    t = snap.get("temp"); u = snap.get("temp_unit", "°C"); p = snap.get("pop_today")
    parts = []
    if t is not None: parts.append(f"{round(t)}{u}")
    if p is not None: parts.append(f"Rain {p}%")
    line = " • ".join(parts) if parts else "—"
    surface.blit(font_small.render(line, True, theme_color), (x, y))

def draw_weather_view(surface, theme_color, digit_color, fonts):
    """Full-screen weather card."""
    font_small, font_tiny, font_regular, font_bold, font_weather_big = fonts
    panel = pygame.Rect(24, 70, WIDTH-48, HEIGHT-110)
    pygame.draw.rect(surface, (35,37,45,210), panel, border_radius=16)
    pygame.draw.rect(surface, theme_color, panel, 2, border_radius=16)

    pad = 20
    x = panel.x + pad
    y = panel.y + pad

    # Header
    draw_text_with_shadow(surface, "Weather", font_regular, (255,255,255), (x, y))
    y += 50

    snap = weather_service.get_snapshot()
    if not snap.get("ok"):
        surface.blit(font_small.render(snap.get("reason","Weather unavailable"), True, (230,230,230)), (x, y))
        return

    # Big temperature
    temp = snap.get("temp"); unit = snap.get("temp_unit","°C")
    if temp is not None:
        big = font_weather_big.render(f"{round(temp)}{unit}", True, digit_color)
        surface.blit(big, (x, y))
        y += big.get_height() + 8

    # Condition
    cond = snap.get("condition","")
    if cond:
        surface.blit(font_small.render(cond, True, (225,225,225)), (x, y))
        y += 30

    # Details row
    feels = snap.get("feels"); hum = snap.get("humidity")
    wind = snap.get("wind"); wind_u = snap.get("wind_unit","kph")
    high = snap.get("high"); low = snap.get("low"); pop = snap.get("pop_today")
    bits = []
    if feels is not None: bits.append(f"Feels {round(feels)}{unit}")
    if hum is not None:   bits.append(f"Humidity {hum}%")
    if wind is not None:  bits.append(f"Wind {round(wind)} {wind_u}")
    if high is not None and low is not None: bits.append(f"Today H {round(high)} / L {round(low)}{unit}")
    if pop is not None: bits.append(f"Rain {pop}%")
    info = "  •  ".join(bits)
    surface.blit(font_small.render(info, True, (210,210,210)), (x, y))

    # Mini forecast (bottom area)
    mini = snap.get("mini", [])
    col_w = (panel.width - 2*pad)//3
    bottom_y = panel.bottom - 120
    surface.blit(font_small.render("Next 3 days", True, (230,230,230)), (x, bottom_y - 28))
    for i, d in enumerate(mini[:3]):
        cx = x + i*col_w; dy = bottom_y
        date_str = d.get("date","")
        try: mmdd = date_str[5:7] + "/" + date_str[8:10]
        except: mmdd = date_str
        surface.blit(font_small.render(mmdd, True, (230,230,230)), (cx, dy)); dy += 26
        hi, lo = d.get("high"), d.get("low")
        if hi is not None and lo is not None:
            surface.blit(font_tiny.render(f"{round(hi)}/{round(lo)}{unit}", True, (210,210,210)), (cx, dy)); dy += 20
        popd = d.get("pop")
        if popd is not None:
            surface.blit(font_tiny.render(f"Rain {popd}%", True, (200,200,200)), (cx, dy)); dy += 18
        cond2 = d.get("cond","")
        if cond2: surface.blit(font_tiny.render(cond2, True, (190,190,190)), (cx, dy))

# --- Pomodoro buttons/adjust state ---
pomo_buttons = {}
pomo_adjust_buttons = {}
pomo_sliders = {}
pomo_active_slider = None
pomo_sliders_initialized = False

# --- Slider class for Adjust view ---
class Slider:
    def __init__(self, rect, min_val, max_val, value, step=1, unit="min"):
        self.track_rect = pygame.Rect(rect)
        self.min = min_val; self.max = max_val; self.step = step
        self.value = max(self.min, min(self.max, value))
        self.unit = unit
        self.handle_radius = 9
        self.dragging = False
        self.handle_rect = pygame.Rect(0,0,self.handle_radius*2,self.handle_radius*2)
        self._reposition_handle()

    def _reposition_handle(self):
        t = (self.value - self.min) / (self.max - self.min)
        hx = int(self.track_rect.x + t * self.track_rect.width)
        self.handle_rect.center = (hx, self.track_rect.centery)

    def set_from_pos(self, x):
        t = (x - self.track_rect.x) / self.track_rect.width
        t = max(0.0, min(1.0, t))
        value = self.min + t*(self.max - self.min)
        value = round(value / self.step) * self.step
        self.value = max(self.min, min(self.max, value))
        self._reposition_handle()

    def draw(self, surface, label, font, theme_color, value_color=(235,235,235)):
        pygame.draw.rect(surface, (70,72,84), self.track_rect, border_radius=6)
        pygame.draw.rect(surface, theme_color, self.track_rect, 2, border_radius=6)
        pygame.draw.circle(surface, theme_color, self.handle_rect.center, self.handle_radius)
        surface.blit(font.render(label, True, (230,230,230)), (self.track_rect.x, self.track_rect.y - 28))
        surface.blit(font.render(f"{int(self.value)} {self.unit}", True, value_color),
                     (self.track_rect.right - 120, self.track_rect.y - 28))

def init_pomo_sliders():
    global pomo_sliders, pomo_sliders_initialized
    pomo_sliders = {}
    padx, start_y = 60, 150
    width = WIDTH - 2*padx
    gap = 70
    pomo_sliders["focus"] = Slider(pygame.Rect(padx, start_y, width, 6), 1, 180, pomodoro_config["focus_minutes"], 1, "min")
    pomo_sliders["short"] = Slider(pygame.Rect(padx, start_y+gap, width, 6), 1, 180, pomodoro_config["short_break_minutes"], 1, "min")
    pomo_sliders["long"]  = Slider(pygame.Rect(padx, start_y+gap*2, width, 6), 1, 180, pomodoro_config["long_break_minutes"], 1, "min")
    pomo_sliders["sessions"] = Slider(pygame.Rect(padx, start_y+gap*3, width, 6), 1, 10, pomodoro_config["sessions_before_long"], 1, "sessions")
    # Volume 0–200%
    initial_gain = int(sound_config.get("gain_percent", 100))
    pomo_sliders["volume"] = Slider(pygame.Rect(padx, start_y+gap*4, width, 6), 0, 200, initial_gain, 5, "%")
    pomo_sliders_initialized = True


def draw_pomodoro_view(surface, theme_color, digit_color, fonts):
    """Pomodoro screen with dynamic ring sizing so time always fits."""
    font_small, font_tiny, font_regular, font_pomo_big = fonts

    panel = pygame.Rect(24, 70, WIDTH-48, HEIGHT-110)
    pygame.draw.rect(surface, (35,37,45,210), panel, border_radius=16)
    pygame.draw.rect(surface, theme_color, panel, 2, border_radius=16)

    pad = 20
    x = panel.x + pad; y = panel.y + pad

    # Mode label on the left
    mode_map = {'focus': 'Focus', 'short_break': 'Break', 'long_break': 'Long Break'}
    draw_text_with_shadow(surface, f"{mode_map.get(pomodoro_timer.mode, 'Focus')}",
                          font_regular, (255,255,255), (x, y))

    # Adjust button on the right
    adjust_rect = pygame.Rect(panel.right - 140, y, 120, 32)
    pygame.draw.rect(surface, theme_color, adjust_rect, border_radius=10)
    surface.blit(font_tiny.render("Adjust", True, (20,20,24)), (adjust_rect.x + 28, adjust_rect.y + 7))
    pomo_buttons['adjust'] = adjust_rect
    y += 54

    # ---------- Fit timer inside ring ----------
    ring_thickness = 12
    timer_text = pomodoro_timer.format_mmss()

    # Max outer diameter allowed by layout (leave space for controls below)
    max_d = min(panel.width - 2*pad, panel.height - 220)
    max_d = max(220, max_d)

    base_size = 110
    timer_font = pygame.font.Font(FONT_BOLD_PATH, base_size)
    t_w, t_h = timer_font.size(timer_text)

    inner_pad = 42
    needed_inner = max(t_w, t_h) + inner_pad
    needed_outer = needed_inner + 2*ring_thickness

    if needed_outer <= max_d:
        diameter = int(min(max_d, needed_outer))
    else:
        inner_target = max_d - 2*ring_thickness
        scale = inner_target / max(1, needed_inner)
        new_size = max(40, int(base_size * scale))
        timer_font = pygame.font.Font(FONT_BOLD_PATH, new_size)
        t_w, t_h = timer_font.size(timer_text)
        diameter = int(max_d)

    ring_rect = pygame.Rect(0, 0, diameter, diameter)
    ring_rect.center = (panel.centerx, panel.centery - 20)

    # Progress ring
    pygame.draw.arc(surface, (80, 82, 96), ring_rect, 0, math.tau, ring_thickness)
    progress = pomodoro_timer.progress_ratio()
    start_ang = -math.pi/2
    end_ang = start_ang + progress * math.tau
    pygame.draw.arc(surface, theme_color, ring_rect, start_ang, end_ang, ring_thickness)

    # Center timer text inside ring
    t_surf = timer_font.render(timer_text, True, digit_color)
    surface.blit(t_surf, t_surf.get_rect(center=ring_rect.center))

    # Info row
    info_y = ring_rect.bottom + 8
    info = f"Session {pomodoro_timer.sessions_completed + (1 if pomodoro_timer.mode!='focus' else 0)}  |  Auto {'ON' if pomodoro_timer.auto_advance else 'OFF'}  |  Sound {'ON' if sound_manager.enabled else 'OFF'}"
    surface.blit(font_small.render(info, True, (220,220,220)), (x, info_y))

    # Controls
    btn_w, btn_h = 120, 40
    gap = 18
    total_w = btn_w*3 + gap*2
    start_x = panel.centerx - total_w//2
    btn_y = info_y + 30

    def draw_btn(key, label):
        rect = pygame.Rect(start_x + order[key]*(btn_w+gap), btn_y, btn_w, btn_h)
        pygame.draw.rect(surface, (55,57,68), rect, border_radius=10)
        pygame.draw.rect(surface, theme_color, rect, 2, border_radius=10)
        label_s = font_small.render(label, True, (240,240,240))
        surface.blit(label_s, label_s.get_rect(center=rect.center))
        pomo_buttons[key] = rect

    order = {'start':0, 'reset':1, 'skip':2}
    draw_btn('start', 'Pause' if pomodoro_timer.running else 'Start')
    draw_btn('reset', 'Reset')
    draw_btn('skip',  'Skip')

    # Toggles: Auto, Sound
    toggle_w, toggle_h = 140, 34
    tog_gap = 16
    tot_w = toggle_w*2 + tog_gap
    start_tx = panel.centerx - tot_w//2
    tog_y = btn_y + btn_h + 18

    auto_rect  = pygame.Rect(start_tx, tog_y, toggle_w, toggle_h)
    sound_rect = pygame.Rect(start_tx + toggle_w + tog_gap, tog_y, toggle_w, toggle_h)

    for r, text in [(auto_rect, f"Auto: {'ON' if pomodoro_timer.auto_advance else 'OFF'}"),
                    (sound_rect, f"Sound: {'ON' if sound_manager.enabled else 'OFF'}")]:
        pygame.draw.rect(surface, (55,57,68), r, border_radius=10)
        pygame.draw.rect(surface, theme_color, r, 2, border_radius=10)
        lbl = font_small.render(text, True, (240,240,240))
        surface.blit(lbl, lbl.get_rect(center=r.center))

    pomo_buttons['auto'] = auto_rect
    pomo_buttons['sound_toggle'] = sound_rect


def draw_pomodoro_adjust_view(surface, theme_color, digit_color, fonts):
    """Sliders for Focus/Short/Long (1–180 min), Sessions (1–10), Volume (0–200%)."""
    global pomo_sliders_initialized
    font_small, font_tiny, font_regular = fonts

    panel = pygame.Rect(24, 70, WIDTH-48, HEIGHT-110)
    pygame.draw.rect(surface, (35,37,45,210), panel, border_radius=16)
    pygame.draw.rect(surface, theme_color, panel, 2, border_radius=16)

    pad = 20
    x = panel.x + pad; y = panel.y + pad
    draw_text_with_shadow(surface, "Adjust Pomodoro", font_regular, (255,255,255), (x, y))

    if not pomo_sliders_initialized:
        init_pomo_sliders()

    labels = [("Focus", "focus"), ("Short break", "short"), ("Long break", "long"),
              ("Sessions before long", "sessions"), ("Volume", "volume")]
    for label, key in labels:
        s = pomo_sliders[key]
        s.draw(surface, label, font_small, theme_color)

    btn_w, btn_h = 140, 40
    gap = 16
    total_w = btn_w*2 + gap
    start_x = panel.centerx - total_w//2
    by = panel.bottom - 60

    save_rect = pygame.Rect(start_x, by, btn_w, btn_h)
    back_rect = pygame.Rect(start_x + btn_w + gap, by, btn_w, btn_h)
    for r, text in [(save_rect, "Save"), (back_rect, "Back")]:
        pygame.draw.rect(surface, (55,57,68), r, border_radius=10)
        pygame.draw.rect(surface, theme_color, r, 2, border_radius=10)
        t = font_small.render(text, True, (240,240,240))
        surface.blit(t, t.get_rect(center=r.center))

    pomo_adjust_buttons['save'] = save_rect
    pomo_adjust_buttons['back'] = back_rect


# =================================================================================
# 7. MAIN APPLICATION
# =================================================================================
clock = pygame.time.Clock()
running = True
dragging = False
offset_x, offset_y = 0, 0

# Chibi animation state
chibi_rect = pygame.Rect(0,0,0,0)
chibi_state = 'normal'
chibi_frame_index = 0
is_in_blink_sequence = False
blink_sequence = [0,1,2,1,0]
blink_sequence_step = 0
last_blink_time = 0
next_blink_delay = random.randint(2000, 5000)
last_frame_update_time = 0
next_state_change_time = 0

# Views & flip animation
app_view = 'main'        # 'main' | 'settings' | 'weather' | 'pomodoro' | 'pomo_adjust'
is_flipping = False
flip_progress = 0.0
flip_direction = 1
from_view = 'main'
to_view = 'main'

theme_buttons, background_buttons, digit_color_buttons = {}, {}, {}
sound_buttons = {}
click_feedback, hover_targets = {}, {}

def start_flip(target_view):
    """Begin a flip from current app_view to target_view."""
    global is_flipping, flip_progress, from_view, to_view, flip_direction, app_view
    if is_flipping or target_view == app_view:
        return
    from_view = app_view
    to_view = target_view
    flip_direction = -1 if target_view == 'main' else 1
    flip_progress = 0.0
    is_flipping = True

while running:
    now = pygame.time.get_ticks()
    mouse_pos = pygame.mouse.get_pos()

    pomodoro_timer.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_button_rect.collidepoint(event.pos):
                running = False

            elif settings_button_rect.collidepoint(event.pos):
                start_flip('main' if app_view == 'settings' else 'settings')

            elif weather_button_rect.collidepoint(event.pos):
                start_flip('main' if app_view == 'weather' else 'weather')

            elif pomodoro_button_rect.collidepoint(event.pos):
                start_flip('main' if app_view in ('pomodoro','pomo_adjust') else 'pomodoro')
                if to_view == 'pomodoro':
                    pomo_sliders_initialized = False

            elif app_view == 'settings':
                for name, rect in theme_buttons.items():
                    if rect.collidepoint(event.pos):
                        current_theme_color = THEMES[name]; click_feedback[name] = {'start_time': now, 'scale': 0.8}; save_settings()
                for name, rect in background_buttons.items():
                    if rect.collidepoint(event.pos):
                        if name == "add_custom": add_custom_background()
                        else: current_background_key = name; click_feedback[name] = {'start_time': now, 'scale': 0.9}; save_settings()
                for name, rect in digit_color_buttons.items():
                    if rect.collidepoint(event.pos):
                        current_digit_color = DIGIT_COLORS[name]; click_feedback[name] = {'start_time': now, 'scale': 0.8}; save_settings()
                for name, rect in sound_buttons.items():
                    if rect.collidepoint(event.pos) and name == "choose_sound": choose_custom_sound()

            elif app_view == 'pomodoro':
                for key, rect in list(pomo_buttons.items()):
                    if rect.collidepoint(event.pos):
                        if key == 'start': pomodoro_timer.toggle()
                        elif key == 'reset': pomodoro_timer.reset()
                        elif key == 'skip': pomodoro_timer.skip()
                        elif key == 'auto': pomodoro_timer.set_auto(not pomodoro_timer.auto_advance); pomodoro_config["auto_advance"] = pomodoro_timer.auto_advance; save_settings()
                        elif key == 'sound_toggle': sound_manager.enabled = not sound_manager.enabled; sound_config["enabled"] = sound_manager.enabled; save_settings()
                        elif key == 'adjust':
                            start_flip('pomo_adjust'); pomo_sliders_initialized = False
                        break

                if win32api and not any(r.collidepoint(event.pos) for r in pomo_buttons.values()) and \
                   not any(r.collidepoint(event.pos) for r in [settings_button_rect, weather_button_rect, pomodoro_button_rect, close_button_rect]):
                    dragging, offset_x, offset_y = True, *event.pos

            elif app_view == 'pomo_adjust':
                for name, s in pomo_sliders.items():
                    if s.track_rect.collidepoint(event.pos) or s.handle_rect.collidepoint(event.pos):
                        pomo_active_slider = name
                        s.set_from_pos(event.pos[0])
                        break
                for key, rect in list(pomo_adjust_buttons.items()):
                    if rect.collidepoint(event.pos):
                        if key == 'save':
                            pomodoro_config["focus_minutes"] = int(pomo_sliders["focus"].value)
                            pomodoro_config["short_break_minutes"] = int(pomo_sliders["short"].value)
                            pomodoro_config["long_break_minutes"] = int(pomo_sliders["long"].value)
                            pomodoro_config["sessions_before_long"] = int(pomo_sliders["sessions"].value)
                            sound_config["gain_percent"] = int(pomo_sliders["volume"].value)
                            pomodoro_timer.focus_minutes = pomodoro_config["focus_minutes"]
                            pomodoro_timer.short_break_minutes = pomodoro_config["short_break_minutes"]
                            pomodoro_timer.long_break_minutes = pomodoro_config["long_break_minutes"]
                            pomodoro_timer.sessions_before_long = pomodoro_config["sessions_before_long"]
                            pomodoro_timer.reset()
                            sound_manager.set_gain_percent(sound_config["gain_percent"])
                            save_settings()
                            start_flip('pomodoro')
                        elif key == 'back':
                            start_flip('pomodoro')
                        break

            elif app_view == 'main':
                if add_task_button_rect.collidepoint(event.pos):
                    task_input_active = not task_input_active
                    if not task_input_active and task_input_text:
                        tasks.append({'id': str(uuid.uuid4()), 'text': task_input_text, 'completed': False})
                        task_input_text = ""; save_tasks(); tasks.sort(key=lambda t: t['completed'])
                elif input_box_rect.collidepoint(event.pos) and task_input_active:
                    pass
                else:
                    if task_input_active:
                        if task_input_text:
                            tasks.append({'id': str(uuid.uuid4()), 'text': task_input_text, 'completed': False})
                            task_input_text = ""; save_tasks(); tasks.sort(key=lambda t: t['completed'])
                        task_input_active = False

                for task_id, rect in list(task_rects.items()):
                    if rect.collidepoint(event.pos):
                        if task_id.endswith('_del'):
                            original_task_id = task_id.replace('_del', '')
                            tasks[:] = [t for t in tasks if t['id'] != original_task_id]
                            save_tasks(); tasks.sort(key=lambda t: t['completed'])
                        else:
                            for task in tasks:
                                if task['id'] == task_id:
                                    task['completed'] = not task['completed']; save_tasks(); tasks.sort(key=lambda t: t['completed']); break
                        break

                if win32api and not add_task_button_rect.collidepoint(event.pos) and \
                   not input_box_rect.collidepoint(event.pos) and \
                   not any(r.collidepoint(event.pos) for r in task_rects.values()) and \
                   not any(r.collidepoint(event.pos) for r in [settings_button_rect, weather_button_rect, pomodoro_button_rect, close_button_rect]):
                    dragging, offset_x, offset_y = True, *event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging = False
            pomo_active_slider = None

        elif event.type == pygame.MOUSEMOTION and win32api:
            if dragging:
                screen_x, screen_y = win32gui.GetCursorPos()
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP,
                                      screen_x - offset_x, screen_y - offset_y, 0, 0,
                                      win32con.SWP_NOSIZE)
            if app_view == 'pomo_adjust' and pomo_active_slider:
                s = pomo_sliders.get(pomo_active_slider)
                if s: s.set_from_pos(event.pos[0])

        elif event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_q, pygame.K_ESCAPE]:
                running = False
            elif task_input_active:
                if event.key == pygame.K_RETURN:
                    if task_input_text:
                        tasks.append({'id': str(uuid.uuid4()), 'text': task_input_text, 'completed': False})
                        task_input_text = ""; save_tasks(); tasks.sort(key=lambda t: t['completed'])
                    task_input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    task_input_text = task_input_text[:-1]
                else:
                    if font_tiny.size(task_input_text + event.unicode)[0] < input_box_rect.width - 20:
                        task_input_text += event.unicode

    # --- Chibi animation ---
    if now > next_state_change_time:
        chibi_state = 'blush' if chibi_state == 'normal' and random.random() < 0.4 else 'normal'
        next_state_change_time = now + random.randint(5000 if chibi_state == 'blush' else 10000,
                                                      8000 if chibi_state == 'blush' else 20000)
    if not is_in_blink_sequence and now - last_blink_time > next_blink_delay:
        is_in_blink_sequence = True; blink_sequence_step = 0
        last_blink_time = now; next_blink_delay = random.randint(2000, 5000)
    if is_in_blink_sequence and now - last_frame_update_time > 75:
        chibi_frame_index = blink_sequence[blink_sequence_step]
        blink_sequence_step += 1; last_frame_update_time = now
        if blink_sequence_step >= len(blink_sequence):
            is_in_blink_sequence = False; blink_sequence_step = 0

    screen.fill(TRANSPARENT_COLOR)
    app_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    # --- Flip animation progress ---
    if is_flipping:
        flip_progress += 0.05
        if flip_progress >= 1.0:
            flip_progress = 1.0; is_flipping = False; app_view = to_view

    current_content_view = to_view if flip_progress > 0.5 else from_view

    # --- Render views ---
    if current_content_view == 'main':
        app_surface.blit(rounded_backgrounds[current_background_key], (0, 0))
        draw_weather_summary_inline(app_surface, (24, 52), (font_small, font_tiny), current_theme_color)

        chibi_y_offset = math.sin(now * 0.001) * 5
        chibi_image = chibi_frames[chibi_state][chibi_frame_index]
        chibi_rect = chibi_image.get_rect(center=(WIDTH // 2, HEIGHT - 100 + chibi_y_offset))
        app_surface.blit(chibi_image, chibi_rect)

        currentTime = datetime.now()
        time_str = currentTime.strftime("%I:%M")
        seconds_str = currentTime.strftime("%S")
        ampm_str = currentTime.strftime("%p")
        date_str = currentTime.strftime("%A, %B %d")

        time_rect = font_bold.render(time_str, True, (0,0,0)).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        draw_text_with_shadow(app_surface, time_str, font_bold, current_digit_color, time_rect.topleft)

        colon_alpha = (math.sin(now*0.002)+1)/2*255
        colon_surface = font_bold.render(":", True, current_digit_color)
        colon_surface.set_alpha(colon_alpha); app_surface.blit(colon_surface, colon_surface.get_rect(center=time_rect.center))

        secondary_color = (100,100,100) if current_digit_color == DIGIT_COLORS["Black"] else (200,200,200)
        app_surface.blit(font_small.render(ampm_str, True, secondary_color), (time_rect.right + 10, time_rect.top + 15))
        app_surface.blit(font_small.render(seconds_str, True, secondary_color), (time_rect.right + 10, time_rect.bottom - 30))

        draw_text_with_shadow(app_surface, date_str, font_regular, current_theme_color,
                              font_regular.render(date_str, True, (0,0,0)).get_rect(center=(WIDTH//2, HEIGHT//2 + 20)).topleft)

        # To-Do List
        draw_text_with_shadow(app_surface, "To-Do List", font_small, (220,220,220), (50, HEIGHT // 2 + 70))
        task_y = HEIGHT // 2 + 110; task_rects = {}
        for task in tasks:
            task_text_color = (150,150,150) if task['completed'] else (255,255,255)
            task_surface = font_tiny.render(task['text'], True, task_text_color)
            task_text_rect = task_surface.get_rect(topleft=(50, task_y))
            app_surface.blit(task_surface, task_text_rect)
            if task['completed']:
                pygame.draw.line(app_surface, task_text_color, (task_text_rect.left, task_text_rect.centery),
                                 (task_text_rect.right, task_text_rect.centery), 1)
            task_rects[task['id']] = task_text_rect
            delete_button_rect = delete_task_icon.get_rect(midleft=(task_text_rect.right + 10, task_text_rect.centery))
            app_surface.blit(delete_task_icon, delete_button_rect)
            task_rects[task['id'] + '_del'] = delete_button_rect
            task_y += 30

        app_surface.blit(add_task_icon, add_task_button_rect)

        if task_input_active:
            pygame.draw.rect(app_surface, (60,60,60), input_box_rect, border_radius=8)
            pygame.draw.rect(app_surface, (100,100,100), input_box_rect, 2, border_radius=8)
            input_text_surface = font_tiny.render(task_input_text, True, (255,255,255))
            app_surface.blit(input_text_surface, (input_box_rect.x + 10, input_box_rect.y + 10))
            if now % 1000 < 500:
                cx = input_box_rect.x + 10 + input_text_surface.get_width()
                pygame.draw.line(app_surface, (255,255,255), (cx, input_box_rect.y + 10), (cx, input_box_rect.y + input_box_rect.height - 10), 2)

    elif current_content_view == 'settings':
        pygame.draw.rect(app_surface, (40,42,54), (0,0,WIDTH,HEIGHT), border_radius=CORNER_RADIUS)
        draw_text_with_shadow(app_surface, "Settings", font_regular, (255,255,255), (30, 30))
        draw_text_with_shadow(app_surface, "Theme Color", font_small, (220,220,220), (50, 100))
        draw_text_with_shadow(app_surface, "Background",  font_small, (220,220,220), (50, 220))
        draw_text_with_shadow(app_surface, "Digit Color", font_small, (220,220,220), (50, 340))
        draw_text_with_shadow(app_surface, "Sound",       font_small, (220,220,220), (50, 460))

        theme_buttons = {}; background_buttons = {}; digit_color_buttons = {}; sound_buttons = {}

        x = 50
        for name, color in THEMES.items():
            rect = pygame.Rect(x, 140, 80, 40); theme_buttons[name] = rect
            feedback = click_feedback.get(name); scale = 1.0
            if feedback:
                elapsed = now - feedback['start_time']
                if elapsed < 200: scale = 0.8 + ease_out_quad(elapsed/200)*0.2
                else: click_feedback.pop(name)
            scaled_rect = rect.inflate((rect.width*scale)-rect.width, (rect.height*scale)-rect.height)
            pygame.draw.rect(app_surface, color, scaled_rect, border_radius=8)
            if current_theme_color == color: pygame.draw.rect(app_surface, (255,255,255), rect, 2, border_radius=8)
            x += 100

        x = 50
        for name, image in raw_backgrounds.items():
            rect = pygame.Rect(x, 260, 100, 60); background_buttons[name] = rect
            feedback = click_feedback.get(name); scale = 1.0
            if feedback:
                elapsed = now - feedback['start_time']
                if elapsed < 200: scale = 0.9 + ease_out_quad(elapsed/200)*0.1
                else: click_feedback.pop(name)
            scaled_rect = rect.inflate((rect.width*scale)-rect.width, (rect.height*scale)-rect.height)
            preview = pygame.transform.scale(rounded_backgrounds[name], scaled_rect.size)
            app_surface.blit(preview, scaled_rect)
            if current_background_key == name: pygame.draw.rect(app_surface, current_theme_color, rect, 2, border_radius=5)
            x += 120

        plus_rect = pygame.Rect(x, 260, 100, 60)
        background_buttons["add_custom"] = plus_rect
        pygame.draw.rect(app_surface, (255,255,255), plus_rect, 2, border_radius=8)
        pygame.draw.line(app_surface, (255,255,255), (plus_rect.centerx - 15, plus_rect.centery), (plus_rect.centerx + 15, plus_rect.centery), 3)
        pygame.draw.line(app_surface, (255,255,255), (plus_rect.centerx, plus_rect.centery - 15), (plus_rect.centerx, plus_rect.centery + 15), 3)

        x = 50
        for name, color in DIGIT_COLORS.items():
            rect = pygame.Rect(x, 380, 80, 40); digit_color_buttons[name] = rect
            feedback = click_feedback.get(name); scale = 1.0
            display_color = color if name != "Black" else (80,80,80)
            if feedback:
                elapsed = now - feedback['start_time']
                if elapsed < 200: scale = 0.8 + ease_out_quad(elapsed/200)*0.2
                else: click_feedback.pop(name)
            scaled_rect = rect.inflate((rect.width*scale)-rect.width, (rect.height*scale)-rect.height)
            pygame.draw.rect(app_surface, display_color, scaled_rect, border_radius=8)
            if current_digit_color == color: pygame.draw.rect(app_surface, (255,255,255), rect, 2, border_radius=8)
            text_color = (0,0,0) if name == "White" else (255,255,255)
            name_surf = font_small.render(name, True, text_color)
            app_surface.blit(name_surf, name_surf.get_rect(center=rect.center))
            x += 100

        choose_rect = pygame.Rect(50, 500, 100, 60)
        sound_buttons["choose_sound"] = choose_rect
        pygame.draw.rect(app_surface, (255,255,255), choose_rect, 2, border_radius=8)
        pygame.draw.line(app_surface, (255,255,255), (choose_rect.centerx - 15, choose_rect.centery), (choose_rect.centerx + 15, choose_rect.centery), 3)
        pygame.draw.line(app_surface, (255,255,255), (choose_rect.centerx, choose_rect.centery - 15), (choose_rect.centerx, choose_rect.centery + 15), 3)
        preview = os.path.basename(sound_config["path"]) if sound_config["path"] else "Default beep / Custom"
        name_surf = font_tiny.render(preview, True, (230,230,230))
        app_surface.blit(name_surf, (choose_rect.right + 12, choose_rect.centery - name_surf.get_height()//2))

    elif current_content_view == 'weather':
        app_surface.blit(rounded_backgrounds[current_background_key], (0,0))
        draw_weather_view(app_surface, current_theme_color, current_digit_color,
                          (font_small, font_tiny, font_regular, font_bold, font_weather_big))

    elif current_content_view == 'pomo_adjust':
        app_surface.blit(rounded_backgrounds[current_background_key], (0,0))
        draw_pomodoro_adjust_view(app_surface, current_theme_color, current_digit_color,
                                  (font_small, font_tiny, font_regular))

    else:  # 'pomodoro'
        app_surface.blit(rounded_backgrounds[current_background_key], (0,0))
        draw_pomodoro_view(app_surface, current_theme_color, current_digit_color,
                           (font_small, font_tiny, font_regular, font_pomo_big))

    # --- Flip perspective effect ---
    eased = ease_in_out_quad(flip_progress); scale_x = math.cos(eased * math.pi)
    anim_width = int(WIDTH * abs(scale_x))
    if anim_width > 0:
        scaled_surface = pygame.transform.scale(app_surface, (anim_width, HEIGHT))
        perspective_shift_amount = 50
        perspective_shift = int((1 - abs(scale_x)) * perspective_shift_amount * flip_direction)
        distorted_surface = pygame.Surface((anim_width, HEIGHT), pygame.SRCALPHA)
        for y in range(HEIGHT):
            row_offset = perspective_shift * ((y - HEIGHT/2) / (HEIGHT/2))
            temp_row_surface = pygame.Surface((anim_width + abs(row_offset)*2, 1), pygame.SRCALPHA)
            temp_row_surface.blit(scaled_surface.subsurface(0, y, anim_width, 1), (abs(row_offset), 0))
            distorted_surface.blit(temp_row_surface.subsurface(abs(row_offset) + row_offset, 0, anim_width, 1), (0, y))
        screen.blit(distorted_surface, ((WIDTH - anim_width)//2, 0))

    # --- Top buttons + hovers ---
    for key, rect in [('settings', settings_button_rect),
                      ('weather',  weather_button_rect),
                      ('pomodoro', pomodoro_button_rect),
                      ('close',    close_button_rect)]:
        if key not in hover_targets:
            hover_targets[key] = {'scale': 1.0, 'angle': 0.0, 'tip_alpha': 0.0}
        is_hover = rect.collidepoint(mouse_pos)
        target_scale = 1.2 if is_hover else 1.0
        target_angle = -15 if is_hover else 0
        target_alpha = 255.0 if is_hover else 0.0
        hover_targets[key]['scale'] += (target_scale - hover_targets[key]['scale']) * 0.2
        hover_targets[key]['angle'] += (target_angle - hover_targets[key]['angle']) * 0.2
        hover_targets[key]['tip_alpha'] += (target_alpha - hover_targets[key]['tip_alpha']) * 0.25

    settings_icon_rot = pygame.transform.rotozoom(settings_icon, hover_targets['settings']['angle'], hover_targets['settings']['scale'])
    screen.blit(settings_icon_rot, settings_icon_rot.get_rect(center=settings_button_rect.center))

    if weather_png is not None:
        weather_icon_rot = pygame.transform.rotozoom(weather_png, hover_targets['weather']['angle'], hover_targets['weather']['scale'])
        screen.blit(weather_icon_rot, weather_icon_rot.get_rect(center=weather_button_rect.center))
    else:
        draw_weather_icon(screen, weather_button_rect, color=(255,255,255))

    if pomodoro_png is not None:
        pomo_icon_rot = pygame.transform.rotozoom(pomodoro_png, hover_targets['pomodoro']['angle'], hover_targets['pomodoro']['scale'])
        screen.blit(pomo_icon_rot, pomo_icon_rot.get_rect(center=pomodoro_button_rect.center))
    else:
        draw_tomato_icon(screen, pomodoro_button_rect)

    close_button_bg_color = (255, 0, 0, 200) if close_button_rect.collidepoint(mouse_pos) else (40, 42, 54, 180)
    btn_surf = pygame.Surface(close_button_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(btn_surf, close_button_bg_color, btn_surf.get_rect(), border_radius=5)
    screen.blit(btn_surf, close_button_rect.topleft)
    close_surf = pygame.transform.rotozoom(font_small.render("X", True, (255,255,255)),
                                           hover_targets['close']['angle'], hover_targets['close']['scale'])
    screen.blit(close_surf, close_surf.get_rect(center=close_button_rect.center))

    # Tooltips
    for key, label, rect in [
        ('settings', 'Settings', settings_button_rect),
        ('weather',  'Weather',  weather_button_rect),
        ('pomodoro', 'Pomodoro', pomodoro_button_rect),
        ('close',    'Close',    close_button_rect),
    ]:
        alpha = int(hover_targets.get(key, {}).get('tip_alpha', 0))
        draw_tooltip(screen, label, rect, font_tiny, alpha)

    pygame.display.flip()
    clock.tick(60)

# =================================================================================
# 9. SAVE SETTINGS & QUIT
# =================================================================================
save_settings()
save_tasks()
if weather_service: weather_service.stop()
pygame.quit()
