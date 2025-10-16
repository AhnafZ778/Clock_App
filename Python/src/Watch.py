# =================================================================================
# 1. IMPORT LIBRARIES
# =================================================================================
import pygame
from datetime import datetime
import os
import math
import random
import json

try:
    import win32api, win32con, win32gui
except ImportError:
    win32api = None

# =================================================================================
# 2. INITIALIZE & SETUP CORE APP VARIABLES
# =================================================================================
pygame.init()
WIDTH, HEIGHT = 600, 600
CORNER_RADIUS = 25
CONFIG_FILE = 'config.json'

# --- Paths ---
script_dir = os.path.dirname(__file__)
assets_dir = os.path.join(script_dir, '..', 'assets')
fonts_dir = os.path.join(assets_dir, 'fonts')
TRANSPARENT_COLOR = (0, 255, 0)
close_button_rect = pygame.Rect(WIDTH - 40, 10, 30, 30)
settings_button_rect = pygame.Rect(10, 10, 30, 30)

# =================================================================================
# 3. CREATE THE CUSTOM WINDOW
# =================================================================================
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Trife Living Clock")
hwnd = None
if win32api:
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0, win32con.LWA_COLORKEY)

# =================================================================================
# 4. LOAD ASSETS & DEFINE THEMES
# =================================================================================
try:
    chibi_frames = {
        'normal': [pygame.image.load(os.path.join(assets_dir, 'open.png')).convert_alpha(), pygame.image.load(os.path.join(assets_dir, 'half.png')).convert_alpha(), pygame.image.load(os.path.join(assets_dir, 'off.png')).convert_alpha()],
        'blush': [pygame.image.load(os.path.join(assets_dir, 'blushOpen.png')).convert_alpha(), pygame.image.load(os.path.join(assets_dir, 'blushhalf.png')).convert_alpha(), pygame.image.load(os.path.join(assets_dir, 'blushClose.png')).convert_alpha()]
    }
    raw_backgrounds = {'bg1': pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg.jpg')).convert_alpha(), (WIDTH, HEIGHT)), 'bg2': pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg_2.jpeg')).convert_alpha(), (WIDTH, HEIGHT))}
    settings_icon = pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'gear.png')).convert_alpha(), (30, 30))
    
    # --- MODIFIED: The filenames are updated to use the new Poppins font ---
    font_bold = pygame.font.Font(os.path.join(fonts_dir, 'Doto-Bold.ttf'), 150)
    font_regular = pygame.font.Font(os.path.join(fonts_dir, 'Doto-Black.ttf'), 36)
    font_small = pygame.font.Font(os.path.join(fonts_dir, 'Doto-Light.ttf'), 24)

except Exception as e:
    print(f"FATAL ERROR: Could not load essential assets: {e}. Please check your assets folder."); exit()

THEMES = {"Purple": (189, 147, 249), "Cyan": (136, 192, 208), "Orange": (255, 184, 108)}

# =================================================================================
# 5. SETTINGS & PERSISTENCE
# =================================================================================
CITY = "Dhaka"; current_background_key = 'bg1'; current_theme_color = THEMES["Purple"]
def load_settings():
    global current_theme_color, current_background_key
    try:
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)
            current_background_key = settings.get('background', current_background_key)
            current_theme_color = THEMES.get(settings.get('theme_name', "Purple"))
    except (FileNotFoundError, json.JSONDecodeError): pass
def save_settings():
    theme_name = [name for name, color in THEMES.items() if color == current_theme_color][0]
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'background': current_background_key, 'theme_name': theme_name}, f, indent=4)
load_settings()

# =================================================================================
# 6. HELPER FUNCTIONS & PRE-RENDERING
# =================================================================================
def apply_rounded_corners(image_surface, radius):
    mask = pygame.Surface(image_surface.get_size(), pygame.SRCALPHA); pygame.draw.rect(mask, (255, 255, 255), (0, 0, *image_surface.get_size()), border_radius=radius)
    rounded_image = image_surface.copy(); rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return rounded_image

def draw_text_with_shadow(surface, text, font, color, position, shadow_color=(0, 0, 0)):
    x, y = position; shadow_surface = font.render(text, True, shadow_color); surface.blit(shadow_surface, (x + 3, y + 3)); text_surface = font.render(text, True, color); surface.blit(text_surface, (x, y))

overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 120))
rounded_backgrounds = {}
for key, bg_image in raw_backgrounds.items():
    temp_surface = bg_image.copy(); temp_surface.blit(overlay, (0, 0)); rounded_backgrounds[key] = apply_rounded_corners(temp_surface, CORNER_RADIUS)

# =================================================================================
# 7. MAIN APPLICATION
# =================================================================================
clock = pygame.time.Clock(); running = True; dragging = False; offset_x, offset_y = 0, 0; chibi_rect = pygame.Rect(0,0,0,0)
chibi_state, chibi_frame_index, is_in_blink_sequence, blink_sequence, blink_sequence_step, last_blink_time, next_blink_delay, last_frame_update_time, next_state_change_time = 'normal', 0, False, [0, 1, 2, 1, 0], 0, 0, random.randint(2000, 5000), 0, 0
app_view, is_flipping, flip_progress, flip_direction = 'main', False, 0.0, 1; theme_buttons, background_buttons = {}, {}

while running:
    now = pygame.time.get_ticks(); mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_button_rect.collidepoint(event.pos): running = False
            elif settings_button_rect.collidepoint(event.pos) and not is_flipping: is_flipping, flip_direction = True, 1 if app_view == 'main' else -1
            elif app_view == 'settings':
                for theme_name, rect in theme_buttons.items():
                    if rect.collidepoint(event.pos): current_theme_color = THEMES[theme_name]
                for bg_name, rect in background_buttons.items():
                    if rect.collidepoint(event.pos): current_background_key = bg_name
            elif app_view == 'main': dragging, offset_x, offset_y = True, *event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: dragging = False
        elif event.type == pygame.MOUSEMOTION and dragging and win32api: screen_x, screen_y = win32gui.GetCursorPos(); win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, screen_x - offset_x, screen_y - offset_y, 0, 0, win32con.SWP_NOSIZE)
        elif event.type == pygame.KEYDOWN and event.key in [pygame.K_q, pygame.K_ESCAPE]: running = False
    
    if is_flipping:
        flip_progress += flip_direction * 0.05
        if flip_progress >= 1.0: flip_progress, is_flipping, app_view = 1.0, False, 'settings'
        elif flip_progress <= 0.0: flip_progress, is_flipping, app_view = 0.0, False, 'main'
    if now > next_state_change_time:
        if chibi_state == 'normal':
            if random.random() < 0.4: chibi_state, next_state_change_time = 'blush', now + random.randint(5000, 8000)
            else: next_state_change_time = now + random.randint(10000, 20000)
        else: chibi_state, next_state_change_time = 'normal', now + random.randint(10000, 20000)
    if not is_in_blink_sequence and now - last_blink_time > next_blink_delay: is_in_blink_sequence, blink_sequence_step, last_blink_time, next_blink_delay = True, 0, now, random.randint(2000, 5000)
    if is_in_blink_sequence and now - last_frame_update_time > 75:
        chibi_frame_index, blink_sequence_step, last_frame_update_time = blink_sequence[blink_sequence_step], blink_sequence_step + 1, now
        if blink_sequence_step >= len(blink_sequence): is_in_blink_sequence, blink_sequence_step = False, 0
    
    screen.fill(TRANSPARENT_COLOR); app_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    view_to_draw = 'settings' if flip_progress > 0.5 else 'main'
    
    if view_to_draw == 'main':
        app_surface.blit(rounded_backgrounds[current_background_key], (0, 0))
        chibi_y_offset = math.sin(now * 0.001) * 5
        if chibi_frames: chibi_image = chibi_frames[chibi_state][chibi_frame_index]; chibi_rect = chibi_image.get_rect(center=(WIDTH // 2, HEIGHT - 100 + chibi_y_offset)); app_surface.blit(chibi_image, chibi_rect)
        currentTime = datetime.now(); time_str, seconds_str, ampm_str, date_str = currentTime.strftime("%I:%M"), currentTime.strftime("%S"), currentTime.strftime("%p"), currentTime.strftime("%A, %B %d")
        time_rect = font_bold.render(time_str, True, (0,0,0)).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)); draw_text_with_shadow(app_surface, time_str, font_bold, (255, 255, 255), time_rect.topleft)
        colon_alpha = (math.sin(now*0.002)+1)/2*255; colon_surface = font_bold.render(":", True, (255, 255, 255)); colon_surface.set_alpha(colon_alpha); app_surface.blit(colon_surface, colon_surface.get_rect(center=time_rect.center))
        ampm_surface = font_small.render(ampm_str, True, (200,200,200)); app_surface.blit(ampm_surface, (time_rect.right + 10, time_rect.top + 15))
        seconds_surface = font_small.render(seconds_str, True, (200,200,200)); app_surface.blit(seconds_surface, (time_rect.right + 10, time_rect.bottom - 30))
        draw_text_with_shadow(app_surface, date_str, font_regular, current_theme_color, font_regular.render(date_str, True, (0,0,0)).get_rect(center=(WIDTH//2, HEIGHT // 2 + 20)).topleft)
    else:
        pygame.draw.rect(app_surface, (40, 42, 54), (0,0,WIDTH,HEIGHT), border_radius=CORNER_RADIUS)
        draw_text_with_shadow(app_surface, "Settings", font_regular, (255,255,255), (30, 30)); draw_text_with_shadow(app_surface, "Theme Color", font_small, (220,220,220), (50, 100)); draw_text_with_shadow(app_surface, "Background", font_small, (220,220,220), (50, 220))
        theme_buttons, x = {}, 50
        for name, color in THEMES.items():
            rect = pygame.Rect(x, 140, 80, 40); theme_buttons[name] = rect; pygame.draw.rect(app_surface, color, rect, border_radius=8)
            if current_theme_color == color: pygame.draw.rect(app_surface, (255,255,255), rect, 3, border_radius=8)
            x += 100
        background_buttons, x = {}, 50
        for name, image in raw_backgrounds.items():
            rect = pygame.Rect(x, 260, 100, 60); background_buttons[name] = rect; app_surface.blit(pygame.transform.scale(image, (100,60)), rect)
            if current_background_key == name: pygame.draw.rect(app_surface, current_theme_color, rect, 3, border_radius=5)
            x += 120
    
    scale_x = math.cos(flip_progress * math.pi); anim_width = int(WIDTH * abs(scale_x))
    if anim_width > 0: scaled_surface = pygame.transform.scale(app_surface, (anim_width, HEIGHT)); screen.blit(scaled_surface, ((WIDTH - anim_width) // 2, 0))
    
    settings_icon_to_draw = settings_icon
    if settings_button_rect.collidepoint(mouse_pos):
        settings_icon_to_draw = pygame.transform.scale(settings_icon, (36, 36))
    screen.blit(settings_icon_to_draw, settings_icon_to_draw.get_rect(center=settings_button_rect.center))
    
    close_button_bg_color = (40, 42, 54, 180)
    if close_button_rect.collidepoint(mouse_pos): close_button_bg_color = (255, 0, 0, 200)
    button_surface = pygame.Surface(close_button_rect.size, pygame.SRCALPHA); pygame.draw.rect(button_surface, close_button_bg_color, button_surface.get_rect(), border_radius=5); screen.blit(button_surface, close_button_rect.topleft)
    
    x_surface = font_small.render("X", True, (255, 255, 255)); x_rect = x_surface.get_rect(center=close_button_rect.center); screen.blit(x_surface, x_rect)

    pygame.display.flip()
    clock.tick(60)

# =================================================================================
# 9. SAVE SETTINGS & QUIT
# =================================================================================
save_settings()
pygame.quit()