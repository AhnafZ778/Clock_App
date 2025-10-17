# =================================================================================
# 1. IMPORT LIBRARIES
# =================================================================================
import pygame
from datetime import datetime
import os
import math
import random
import json
import uuid # For unique task IDs

try:
    import win32api, win32con, win32gui
except ImportError:
    win32api = None
    print("Warning: 'pywin32' not found. Window transparency and dragging will be disabled.")


# =================================================================================
# 2. INITIALIZE & SETUP CORE APP VARIABLES
# =================================================================================
pygame.init()
WIDTH, HEIGHT = 600, 600
CORNER_RADIUS = 25
CONFIG_FILE = 'config.json'
TODO_FILE = 'todo.json' # File for to-do list persistence

# --- Paths ---
script_dir = os.path.dirname(__file__)
# Adjusting assets_dir to look in 'assets' folder directly within the script's directory
# If your assets are in 'Clock_App/assets' and script in 'Clock_App/Python/src',
# then 'os.path.join(script_dir, '..', '..', 'assets')' might be needed.
# For simplicity, assuming 'assets' is a sibling to 'src'.
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
if win32api: # Only apply window attributes if pywin32 is available
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
    
    _temp_raw_backgrounds = {}
    _temp_raw_backgrounds['bg1'] = pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg.jpg')).convert_alpha(), (WIDTH, HEIGHT))
    try:
        _temp_raw_backgrounds['bg3'] = pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg3.jpg')).convert_alpha(), (WIDTH, HEIGHT))
    except FileNotFoundError:
        print("Warning: 'bg3.jpg' not found. Using 'bg1.jpg' as a fallback.")
    raw_backgrounds = _temp_raw_backgrounds

    settings_icon = pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'gear.png')).convert_alpha(), (30, 30))
    
    # To-Do list icons - Ensure these files exist or use the commented-out placeholder generation
    # add_task_icon = pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'add_icon.png')).convert_alpha(), (20, 20)) 
    # delete_task_icon = pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'delete_icon.png')).convert_alpha(), (20, 20))
    
    # Placeholder icons if you don't have image files yet
    add_task_icon = pygame.Surface((20,20), pygame.SRCALPHA); pygame.draw.circle(add_task_icon, (100,255,100), (10,10), 9); pygame.draw.line(add_task_icon, (0,0,0), (10,5), (10,15), 2); pygame.draw.line(add_task_icon, (0,0,0), (5,10), (15,10), 2)
    delete_task_icon = pygame.Surface((20,20), pygame.SRCALPHA); pygame.draw.circle(delete_task_icon, (255,100,100), (10,10), 9); pygame.draw.line(delete_task_icon, (0,0,0), (5,5), (15,15), 2); pygame.draw.line(delete_task_icon, (0,0,0), (5,15), (15,5), 2)


    font_bold = pygame.font.Font(os.path.join(fonts_dir, 'Doto_Rounded-Bold.ttf'), 150)
    font_regular = pygame.font.Font(os.path.join(fonts_dir, 'Doto_Rounded-Regular.ttf'), 36)
    font_small = pygame.font.Font(os.path.join(fonts_dir, 'Doto_Rounded-Regular.ttf'), 24)
    font_tiny = pygame.font.Font(os.path.join(fonts_dir, 'Doto_Rounded-Regular.ttf'), 18) # Smaller font for tasks

except Exception as e:
    print(f"FATAL ERROR: Could not load essential assets: {e}. Please check your assets folder and font files."); exit()

THEMES = {"Purple": (189, 147, 249), "Cyan": (136, 192, 208), "Orange": (255, 184, 108)}
DIGIT_COLORS = {"White": (255, 255, 255), "Black": (0, 0, 0), "Gray": (200, 200, 200)}

# =================================================================================
# 5. SETTINGS & PERSISTENCE
# =================================================================================
current_background_key = 'bg1'; current_theme_color = THEMES["Purple"]
current_digit_color = DIGIT_COLORS["White"]
tasks = [] # Global list to hold our tasks

def load_settings():
    global current_theme_color, current_background_key, current_digit_color
    try:
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)
            loaded_bg_key = settings.get('background', current_background_key)
            if loaded_bg_key in raw_backgrounds:
                current_background_key = loaded_bg_key
            else:
                current_background_key = 'bg1'
            
            current_theme_color = THEMES.get(settings.get('theme_name', "Purple"))

            loaded_digit_color_name = settings.get('digit_color_name', "White")
            current_digit_color = DIGIT_COLORS.get(loaded_digit_color_name, DIGIT_COLORS["White"])
    except (FileNotFoundError, json.JSONDecodeError):
        save_settings() # Save defaults if config doesn't exist or is malformed

def save_settings():
    theme_name = [name for name, color in THEMES.items() if color == current_theme_color][0]
    digit_color_name = [name for name, color in DIGIT_COLORS.items() if color == current_digit_color][0]
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'background': current_background_key, 'theme_name': theme_name, 'digit_color_name': digit_color_name}, f, indent=4)

# To-Do list persistence functions
def load_tasks():
    global tasks
    try:
        with open(TODO_FILE, 'r') as f:
            tasks_data = json.load(f)
        tasks = []
        for task in tasks_data:
            # Ensure 'id' exists and convert to str if needed
            if 'id' not in task:
                task['id'] = str(uuid.uuid4())
            else:
                task['id'] = str(task['id']) # Ensure it's a string for consistency
            tasks.append(task)
    except (FileNotFoundError, json.JSONDecodeError):
        tasks = [] # Start with an empty list if file doesn't exist or is invalid
    # Sort tasks: incomplete first, then completed
    tasks.sort(key=lambda t: t['completed']) 

def save_tasks():
    with open(TODO_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

load_settings() # Load settings on startup
load_tasks()    # Load tasks on startup

# =================================================================================
# 6. HELPER FUNCTIONS & PRE-RENDERING
# =================================================================================
def apply_rounded_corners(image_surface, radius):
    mask = pygame.Surface(image_surface.get_size(), pygame.SRCALPHA); pygame.draw.rect(mask, (255, 255, 255), (0, 0, *image_surface.get_size()), border_radius=radius)
    rounded_image = image_surface.copy(); rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return rounded_image

def draw_text_with_shadow(surface, text, font, color, position, shadow_color=(0, 0, 0)):
    x, y = position; shadow_surface = font.render(text, True, shadow_color); surface.blit(shadow_surface, (x + 3, y + 3)); text_surface = font.render(text, True, color); surface.blit(text_surface, (x, y))

# Easing functions for animations
def ease_out_quad(t):
    return t * (2 - t)
def ease_in_out_quad(t):
    # This version is better for starting and ending smoothly
    return t * t * 2 if t < 0.5 else (-2 * t * t) + (4 * t) - 1

overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 80))

rounded_backgrounds = {}
for key, bg_image in raw_backgrounds.items():
    temp_surface = bg_image.copy(); temp_surface.blit(overlay, (0, 0)); rounded_backgrounds[key] = apply_rounded_corners(temp_surface, CORNER_RADIUS)

# To-Do list related variables for UI
add_task_button_rect = pygame.Rect(WIDTH - 50, HEIGHT - 50, 30, 30) 
task_input_active = False 
task_input_text = "" 
input_box_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT - 80, 300, 40)
task_rects = {} # Stores pygame.Rect for each task to check clicks

# =================================================================================
# 7. MAIN APPLICATION
# =================================================================================
clock = pygame.time.Clock(); running = True; dragging = False; offset_x, offset_y = 0, 0; chibi_rect = pygame.Rect(0,0,0,0)
chibi_state, chibi_frame_index, is_in_blink_sequence, blink_sequence, blink_sequence_step, last_blink_time, next_blink_delay, last_frame_update_time, next_state_change_time = 'normal', 0, False, [0, 1, 2, 1, 0], 0, 0, random.randint(2000, 5000), 0, 0
app_view, is_flipping, flip_progress, flip_direction = 'main', False, 0.0, 1; theme_buttons, background_buttons = {}, {}
digit_color_buttons = {}
click_feedback = {}; hover_targets = {}

while running:
    now = pygame.time.get_ticks(); mouse_pos = pygame.mouse.get_pos()
    
    # --- DEBUGGING PRINTS AND VISUALS ---
    # Draw a debug rectangle for the settings button's click area
    if settings_button_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, (255, 255, 0, 150), settings_button_rect.inflate(5,5), 2, border_radius=5) # Yellow border around hover
        # print("DEBUG: Mouse HOVERING over settings button") # Uncomment for console feedback
    
    # Print the state of is_flipping to see if it's stuck
    # print(f"DEBUG: is_flipping: {is_flipping}, flip_progress: {flip_progress:.2f}, app_view: {app_view}")
    # --- END DEBUGGING ---

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_button_rect.collidepoint(event.pos): running = False
            
            # This is the critical line for the settings button
            if settings_button_rect.collidepoint(event.pos):
                print("DEBUG: Settings button CLICK DETECTED!") # Always print on click
                if not is_flipping: # Check the condition that allows the flip
                    print(f"DEBUG: Initiating flip. Current view: {app_view}")
                    is_flipping, flip_direction = True, 1 if app_view == 'main' else -1
                    flip_progress = 0.0 if flip_direction == 1 else 1.0 # Ensure fresh start
                else:
                    print("DEBUG: Settings button clicked, but flip is currently active. Not initiating new flip.")
            
            elif app_view == 'settings':
                for name, rect in theme_buttons.items():
                    if rect.collidepoint(event.pos): current_theme_color, click_feedback[name] = THEMES[name], {'start_time': now, 'scale': 0.8}; save_settings()
                for name, rect in background_buttons.items():
                    if rect.collidepoint(event.pos): current_background_key, click_feedback[name] = name, {'start_time': now, 'scale': 0.9}; save_settings()
                for name, rect in digit_color_buttons.items():
                    if rect.collidepoint(event.pos): current_digit_color, click_feedback[name] = DIGIT_COLORS[name], {'start_time': now, 'scale': 0.8}; save_settings()
            elif app_view == 'main':
                # To-Do list interaction (unchanged from previous version)
                if add_task_button_rect.collidepoint(event.pos):
                    task_input_active = not task_input_active 
                    if not task_input_active and task_input_text: 
                        tasks.append({'id': str(uuid.uuid4()), 'text': task_input_text, 'completed': False})
                        task_input_text = ""
                        save_tasks()
                        tasks.sort(key=lambda t: t['completed']) 
                elif input_box_rect.collidepoint(event.pos) and task_input_active:
                    pass 
                else: 
                    if task_input_active:
                        if task_input_text: 
                            tasks.append({'id': str(uuid.uuid4()), 'text': task_input_text, 'completed': False})
                            task_input_text = ""
                            save_tasks()
                            tasks.sort(key=lambda t: t['completed'])
                        task_input_active = False
                
                # Check if a task or delete button was clicked
                for task_id, rect in list(task_rects.items()): 
                    if rect.collidepoint(event.pos):
                        if task_id.endswith('_del'): 
                            original_task_id = task_id.replace('_del', '')
                            tasks = [t for t in tasks if t['id'] != original_task_id]
                            save_tasks()
                            tasks.sort(key=lambda t: t['completed']) 
                        else: 
                            for task in tasks:
                                if task['id'] == task_id:
                                    task['completed'] = not task['completed']
                                    save_tasks()
                                    tasks.sort(key=lambda t: t['completed']) 
                                    break
                        break 

                # Handle dragging for main view, ensuring it doesn't interfere with task buttons/input
                if win32api and not add_task_button_rect.collidepoint(event.pos) and \
                   not input_box_rect.collidepoint(event.pos) and \
                   not any(r.collidepoint(event.pos) for r in task_rects.values()) and \
                   not settings_button_rect.collidepoint(event.pos) and \
                   not close_button_rect.collidepoint(event.pos): # Added checks for settings/close buttons
                    dragging, offset_x, offset_y = True, *event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: dragging = False
        elif event.type == pygame.MOUSEMOTION and dragging and win32api: 
            screen_x, screen_y = win32gui.GetCursorPos()
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, screen_x - offset_x, screen_y - offset_y, 0, 0, win32con.SWP_NOSIZE)
        elif event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_q, pygame.K_ESCAPE]: running = False
            elif task_input_active:
                if event.key == pygame.K_RETURN:
                    if task_input_text:
                        tasks.append({'id': str(uuid.uuid4()), 'text': task_input_text, 'completed': False})
                        task_input_text = ""
                        save_tasks()
                        tasks.sort(key=lambda t: t['completed'])
                    task_input_active = False 
                elif event.key == pygame.K_BACKSPACE:
                    task_input_text = task_input_text[:-1]
                else:
                    if font_tiny.size(task_input_text + event.unicode)[0] < input_box_rect.width - 20:
                        task_input_text += event.unicode
    
    # Chibi animation logic (unchanged)
    if now > next_state_change_time:
        chibi_state = 'blush' if chibi_state == 'normal' and random.random() < 0.4 else 'normal'
        next_state_change_time = now + random.randint(5000 if chibi_state == 'blush' else 10000, 8000 if chibi_state == 'blush' else 20000)
    if not is_in_blink_sequence and now - last_blink_time > next_blink_delay: is_in_blink_sequence, blink_sequence_step, last_blink_time, next_blink_delay = True, 0, now, random.randint(2000, 5000)
    if is_in_blink_sequence and now - last_frame_update_time > 75: 
        chibi_frame_index, blink_sequence_step, last_frame_update_time = blink_sequence[blink_sequence_step], blink_sequence_step + 1, now
        if blink_sequence_step >= len(blink_sequence): is_in_blink_sequence, blink_sequence_step = False, 0
    
    screen.fill(TRANSPARENT_COLOR); app_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    # === Flip Progress Update Logic ===
    if is_flipping:
        flip_progress += flip_direction * 0.05 # Reduced speed slightly for better visual
        # Ensure progress stays within 0.0 and 1.0
        flip_progress = max(0.0, min(1.0, flip_progress)) 

        if flip_progress >= 1.0 and flip_direction == 1: # Fully flipped to settings
            flip_progress, is_flipping, app_view = 1.0, False, 'settings'
            print("DEBUG: Flip to SETTINGS complete.") # Debug message
        elif flip_progress <= 0.0 and flip_direction == -1: # Fully flipped to main
            flip_progress, is_flipping, app_view = 0.0, False, 'main'
            print("DEBUG: Flip to MAIN complete.") # Debug message
    # === End Flip Progress Update Logic ===

    current_content_view = 'settings' if flip_progress > 0.5 else 'main'
    
    if current_content_view == 'main':
        app_surface.blit(rounded_backgrounds[current_background_key], (0, 0))
        chibi_y_offset = math.sin(now * 0.001) * 5
        if chibi_frames: chibi_image = chibi_frames[chibi_state][chibi_frame_index]; chibi_rect = chibi_image.get_rect(center=(WIDTH // 2, HEIGHT - 100 + chibi_y_offset)); app_surface.blit(chibi_image, chibi_rect)
        
        currentTime = datetime.now()
        time_str = currentTime.strftime("%I:%M")
        seconds_str = currentTime.strftime("%S")
        ampm_str = currentTime.strftime("%p")
        date_str = currentTime.strftime("%A, %B %d")
        
        time_rect = font_bold.render(time_str, True, (0,0,0)).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)); draw_text_with_shadow(app_surface, time_str, font_bold, current_digit_color, time_rect.topleft)
        
        colon_alpha = (math.sin(now*0.002)+1)/2*255; colon_surface = font_bold.render(":", True, current_digit_color); colon_surface.set_alpha(colon_alpha); app_surface.blit(colon_surface, colon_surface.get_rect(center=time_rect.center))
        
        if current_digit_color == DIGIT_COLORS["Black"]:
            secondary_color = (100, 100, 100)
        else:
            secondary_color = (200, 200, 200)

        ampm_surface = font_small.render(ampm_str, True, secondary_color); app_surface.blit(ampm_surface, (time_rect.right + 10, time_rect.top + 15))
        seconds_surface = font_small.render(seconds_str, True, secondary_color); app_surface.blit(seconds_surface, (time_rect.right + 10, time_rect.bottom - 30))
        
        draw_text_with_shadow(app_surface, date_str, font_regular, current_theme_color, font_regular.render(date_str, True, (0,0,0)).get_rect(center=(WIDTH//2, HEIGHT // 2 + 20)).topleft)

        # Draw To-Do List (unchanged)
        draw_text_with_shadow(app_surface, "To-Do List", font_small, (220, 220, 220), (50, HEIGHT // 2 + 70))
        task_y = HEIGHT // 2 + 110
        task_rects = {} 

        for task in tasks:
            task_text_color = (150, 150, 150) if task['completed'] else (255, 255, 255)
            task_surface = font_tiny.render(task['text'], True, task_text_color)
            task_text_rect = task_surface.get_rect(topleft=(50, task_y))
            app_surface.blit(task_surface, task_text_rect)

            if task['completed']:
                pygame.draw.line(app_surface, task_text_color, 
                                 (task_text_rect.left, task_text_rect.centery), 
                                 (task_text_rect.right, task_text_rect.centery), 1)
            
            task_rects[task['id']] = task_text_rect

            delete_button_rect = delete_task_icon.get_rect(midleft=(task_text_rect.right + 10, task_text_rect.centery))
            app_surface.blit(delete_task_icon, delete_button_rect)
            task_rects[task['id'] + '_del'] = delete_button_rect 

            task_y += 30 

        app_surface.blit(add_task_icon, add_task_button_rect)

        if task_input_active:
            pygame.draw.rect(app_surface, (60, 60, 60), input_box_rect, border_radius=8)
            pygame.draw.rect(app_surface, (100, 100, 100), input_box_rect, 2, border_radius=8) 
            input_text_surface = font_tiny.render(task_input_text, True, (255, 255, 255))
            app_surface.blit(input_text_surface, (input_box_rect.x + 10, input_box_rect.y + 10))
            if now % 1000 < 500: 
                cursor_x = input_box_rect.x + 10 + input_text_surface.get_width()
                pygame.draw.line(app_surface, (255,255,255), (cursor_x, input_box_rect.y + 10), (cursor_x, input_box_rect.y + input_box_rect.height - 10), 2)


    else: # Settings View (unchanged)
        pygame.draw.rect(app_surface, (40, 42, 54), (0,0,WIDTH,HEIGHT), border_radius=CORNER_RADIUS)
        draw_text_with_shadow(app_surface, "Settings", font_regular, (255,255,255), (30, 30))
        draw_text_with_shadow(app_surface, "Theme Color", font_small, (220,220,220), (50, 100))
        draw_text_with_shadow(app_surface, "Background", font_small, (220,220,220), (50, 220))
        draw_text_with_shadow(app_surface, "Digit Color", font_small, (220,220,220), (50, 340))

        # Theme Color Buttons
        x = 50
        for name, color in THEMES.items():
            rect = pygame.Rect(x, 140, 80, 40); theme_buttons[name] = rect
            feedback = click_feedback.get(name)
            scale = 1.0
            if feedback:
                elapsed = now - feedback['start_time']
                if elapsed < 200: scale = 0.8 + ease_out_quad(elapsed/200) * 0.2
                else: click_feedback.pop(name)
            
            scaled_rect = rect.inflate((rect.width*scale)-rect.width, (rect.height*scale)-rect.height)
            pygame.draw.rect(app_surface, color, scaled_rect, border_radius=8)
            if current_theme_color == color: pygame.draw.rect(app_surface, (255,255,255), rect, 2, border_radius=8)
            x += 100
        
        # Background Buttons
        x = 50
        for name, image in raw_backgrounds.items():
            rect = pygame.Rect(x, 260, 100, 60); background_buttons[name] = rect
            feedback = click_feedback.get(name)
            scale = 1.0
            if feedback:
                elapsed = now - feedback['start_time']
                if elapsed < 200: scale = 0.9 + ease_out_quad(elapsed/200) * 0.1
                else: click_feedback.pop(name)
            
            scaled_rect = rect.inflate((rect.width*scale)-rect.width, (rect.height*scale)-rect.height)
            app_surface.blit(pygame.transform.scale(image, scaled_rect.size), scaled_rect)
            if current_background_key == name: pygame.draw.rect(app_surface, current_theme_color, rect, 2, border_radius=5)
            x += 120

        # Digit Color Buttons
        x = 50
        for name, color in DIGIT_COLORS.items():
            rect = pygame.Rect(x, 380, 80, 40)
            digit_color_buttons[name] = rect
            feedback = click_feedback.get(name)
            
            display_color = color if name != "Black" else (80, 80, 80)
            
            scale = 1.0
            if feedback:
                elapsed = now - feedback['start_time']
                if elapsed < 200: scale = 0.8 + ease_out_quad(elapsed/200) * 0.2
                else: click_feedback.pop(name)
            
            scaled_rect = rect.inflate((rect.width*scale)-rect.width, (rect.height*scale)-rect.height)
            pygame.draw.rect(app_surface, display_color, scaled_rect, border_radius=8)
            
            if current_digit_color == color:
                pygame.draw.rect(app_surface, (255,255,255), rect, 2, border_radius=8)
            
            text_color = (0,0,0) if name == "White" else (255,255,255)
            text_surf = font_small.render(name, True, text_color)
            text_rect = text_surf.get_rect(center=rect.center)
            app_surface.blit(text_surf, text_rect)

            x += 100
    
    # Settings flip animation with perspective (unchanged, but moved the flip logic above it)
    eased_flip_progress = ease_in_out_quad(flip_progress)
    scale_x = math.cos(eased_flip_progress * math.pi)
    anim_width = int(WIDTH * abs(scale_x))

    if anim_width > 0:
        scaled_surface = pygame.transform.scale(app_surface, (anim_width, HEIGHT))
        perspective_shift_amount = 50 
        perspective_shift = int((1 - abs(scale_x)) * perspective_shift_amount * flip_direction)
        
        distorted_surface = pygame.Surface((anim_width, HEIGHT), pygame.SRCALPHA)
        
        for y in range(HEIGHT):
            row_perspective_offset = perspective_shift * ((y - HEIGHT/2) / (HEIGHT/2)) 
            if anim_width > 0:
                temp_row_surface = pygame.Surface((anim_width + abs(row_perspective_offset)*2, 1), pygame.SRCALPHA)
                temp_row_surface.blit(scaled_surface.subsurface(0, y, anim_width, 1), (abs(row_perspective_offset), 0))
                distorted_surface.blit(temp_row_surface.subsurface(abs(row_perspective_offset) + row_perspective_offset, 0, anim_width, 1), (0, y))
            else:
                pass # Should not be reached due to 'if anim_width > 0'
        screen.blit(distorted_surface, ((WIDTH - anim_width) // 2, 0))
    
    # Top buttons (settings and close) are drawn AFTER the app_surface flip
    for key, rect in [('settings', settings_button_rect), ('close', close_button_rect)]:
        if key not in hover_targets: hover_targets[key] = {'scale': 1.0, 'angle': 0.0}
        
        target_scale = 1.2 if rect.collidepoint(mouse_pos) else 1.0
        target_angle = -15 if rect.collidepoint(mouse_pos) else 0
        
        hover_targets[key]['scale'] += (target_scale - hover_targets[key]['scale']) * 0.2
        hover_targets[key]['angle'] += (target_angle - hover_targets[key]['angle']) * 0.2
    
    settings_icon_rotated = pygame.transform.rotozoom(settings_icon, hover_targets['settings']['angle'], hover_targets['settings']['scale'])
    screen.blit(settings_icon_rotated, settings_icon_rotated.get_rect(center=settings_button_rect.center))
    
    close_button_bg_color = (255, 0, 0, 200) if close_button_rect.collidepoint(mouse_pos) else (40, 42, 54, 180)
    button_surface = pygame.Surface(close_button_rect.size, pygame.SRCALPHA); pygame.draw.rect(button_surface, close_button_bg_color, button_surface.get_rect(), border_radius=5); screen.blit(button_surface, close_button_rect.topleft)
    
    close_icon_color = (255,255,255)
    close_surf = pygame.transform.rotozoom(font_small.render("X", True, close_icon_color), hover_targets['close']['angle'], hover_targets['close']['scale'])
    screen.blit(close_surf, close_surf.get_rect(center=close_button_rect.center))

    pygame.display.flip()
    clock.tick(60)

# =================================================================================
# 9. SAVE SETTINGS & QUIT
# =================================================================================
save_settings()
save_tasks() 
pygame.quit()