# =================================================================================
# 1. IMPORT LIBRARIES
# =================================================================================
import pygame
from datetime import datetime
import os
import math

try:
    import win32api
    import win32con
    import win32gui
except ImportError:
    print("pywin32 is not installed. The window will not be transparent, rounded, or draggable.")
    win32api = None

# =================================================================================
# 2. INITIALIZE PYGAME
# =================================================================================
pygame.init()

# =================================================================================
# 3. SETUP PATHS and CONSTANTS
# =================================================================================
WIDTH, HEIGHT = 600, 600
CORNER_RADIUS = 25
script_dir = os.path.dirname(__file__)
assets_dir = os.path.join(script_dir, '..', 'assets')
fonts_dir = os.path.join(assets_dir, 'fonts')
TRANSPARENT_COLOR = (0, 255, 0)

# --- FIX: Define the close button's rectangle here, once. ---
# By defining it outside the main loop, it becomes a reliable constant that
# doesn't need to be recalculated every frame.
close_button_rect = pygame.Rect(WIDTH - 40, 10, 30, 30)

# =================================================================================
# 4. CREATE THE GAME WINDOW and MAKE IT TRANSPARENT
# =================================================================================
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Trife Modern Clock")

hwnd = None
if win32api:
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0, win32con.LWA_COLORKEY)

# ... (Asset loading and helper functions remain the same) ...
# =================================================================================
# 5. HELPER FUNCTION FOR MASKING & 6. LOAD ASSETS
# =================================================================================
def apply_rounded_corners(image_surface, radius):
    mask = pygame.Surface(image_surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255), (0, 0, *image_surface.get_size()), border_radius=radius)
    rounded_image = image_surface.copy()
    rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return rounded_image

try:
    raw_backgrounds = {
        'bg1': pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg.jpg')).convert_alpha(), (WIDTH, HEIGHT)),
        'bg2': pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg_2.jpeg')).convert_alpha(), (WIDTH, HEIGHT))
    }
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    rounded_backgrounds = {}
    for key, bg_image in raw_backgrounds.items():
        temp_surface = bg_image.copy()
        temp_surface.blit(overlay, (0, 0))
        rounded_backgrounds[key] = apply_rounded_corners(temp_surface, CORNER_RADIUS)
    current_background = rounded_backgrounds['bg1']
except FileNotFoundError:
    current_background = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(current_background, (40, 42, 54), (0,0,WIDTH,HEIGHT), border_radius=CORNER_RADIUS)

try:
    font_bold = pygame.font.Font(os.path.join(fonts_dir, 'Inter-Bold.ttf'), 128)
    font_regular = pygame.font.Font(os.path.join(fonts_dir, 'Inter-Regular.ttf'), 32)
except FileNotFoundError:
    font_bold = pygame.font.Font(None, 150)
    font_regular = pygame.font.Font(None, 40)

def draw_text_with_shadow(surface, text, font, color, position, shadow_color=(0, 0, 0)):
    x, y = position
    shadow_surface = font.render(text, True, shadow_color)
    surface.blit(shadow_surface, (x + 3, y + 3))
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, (x, y))

clock = pygame.time.Clock()
# =================================================================================
# 7. MAIN APPLICATION LOOP
# =================================================================================
running = True
dragging = False
offset_x, offset_y = 0, 0

while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # --- FIX: This is the corrected logic block ---
                # FIRST, we check if the click was on the close button.
                if close_button_rect.collidepoint(event.pos):
                    # If it was, we set running to False to end the program.
                    running = False
                # ELSE, if the click was anywhere else...
                else:
                    # ...we start dragging.
                    dragging = True
                    offset_x, offset_y = event.pos

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if dragging and win32api:
                screen_x, screen_y = win32gui.GetCursorPos()
                new_x = screen_x - offset_x
                new_y = screen_y - offset_y
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, new_x, new_y, 0, 0, win32con.SWP_NOSIZE)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_0:
                current_background = rounded_backgrounds['bg1']
            if event.key == pygame.K_1:
                current_background = rounded_backgrounds['bg2']

    # --- Drawing Logic ---
    mouse_pos = pygame.mouse.get_pos()
    screen.fill(TRANSPARENT_COLOR)
    screen.blit(current_background, (0, 0))
    
    # ... (The rest of the drawing code is unchanged) ...
    currentTime = datetime.now()
    time_str = currentTime.strftime("%I:%M")
    seconds_str = currentTime.strftime("%S")
    ampm_str = currentTime.strftime("%p")
    date_str = currentTime.strftime("%A, %B %d")

    time_rect = font_bold.render(time_str, True, (0,0,0)).get_rect(center=(WIDTH // 2, HEIGHT // 2))
    draw_text_with_shadow(screen, time_str, font_bold, (255, 255, 255), time_rect.topleft)
    
    colon_alpha = (math.sin(pygame.time.get_ticks() * 0.002) + 1) / 2 * 255
    colon_surface = font_bold.render(":", True, (255, 255, 255))
    colon_surface.set_alpha(colon_alpha)
    colon_rect = colon_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(colon_surface, colon_rect)
    
    seconds_pos = (time_rect.right + 15, time_rect.centery + 15)
    ampm_pos = (time_rect.right + 15, time_rect.centery - 25)
    date_rect = font_regular.render(date_str, True, (0,0,0)).get_rect(center=(WIDTH // 2, HEIGHT - 60))
    draw_text_with_shadow(screen, seconds_str, font_regular, (200, 200, 200), seconds_pos)
    draw_text_with_shadow(screen, ampm_str, font_regular, (200, 200, 200), ampm_pos)
    draw_text_with_shadow(screen, date_str, font_regular, (220, 220, 220), date_rect.topleft)
    
    # We use the constant 'close_button_rect' here for both checking the hover and drawing.
    close_button_bg_color = (40, 42, 54, 180)
    if close_button_rect.collidepoint(mouse_pos):
        close_button_bg_color = (255, 0, 0, 200)
        
    button_surface = pygame.Surface(close_button_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(button_surface, close_button_bg_color, button_surface.get_rect(), border_radius=5)
    screen.blit(button_surface, close_button_rect.topleft)
    
    draw_text_with_shadow(screen, "X", font_regular, (255, 255, 255), (WIDTH - 33, 8))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()