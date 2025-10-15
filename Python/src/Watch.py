# =================================================================================
# 1. IMPORT LIBRARIES
# We need to import the libraries that give us the tools we need.
# =================================================================================

import pygame           # The main library for creating the window, drawing, and handling events.
from datetime import datetime  # Used to get the current date and time.
import os               # Helps us work with files and directories (finding our assets folder).
import math             # Gives us access to advanced math functions, like sine for the smooth blink.

# =================================================================================
# 2. INITIALIZE PYGAME
# This function must be called at the very beginning to set up Pygame's modules.
# =================================================================================
pygame.init()

# =================================================================================
# 3. SETUP PATHS and CONSTANTS
# We define our window size and create reliable paths to our asset folders.
# This makes sure the script can always find its images and fonts.
# =================================================================================

# --- Window Dimensions ---
WIDTH, HEIGHT = 600, 600

# --- File Paths ---
# This line gets the full path to the directory where this script is located (e.g., 'D:/.../src').
script_dir = os.path.dirname(__file__)
# This line goes one level up ('..') from the 'src' directory to find the 'Python' directory,
# then it joins that path with the 'assets' folder name.
assets_dir = os.path.join(script_dir, '..', 'assets')
# This creates a specific path to our new 'fonts' folder inside 'assets'.
fonts_dir = os.path.join(assets_dir, 'fonts')

# =================================================================================
# 4. CREATE THE GAME WINDOW
# This is where we create the main window for our application.
# =================================================================================

# We create the display. pygame.NOFRAME removes the default title bar and border.
# If you want the standard window border and X button back, change this line to:
# screen = pygame.display.set_mode((WIDTH, HEIGHT))
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)

# This sets the name that appears in the taskbar.
pygame.display.set_caption("Trife Modern Clock")

# =================================================================================
# 5. LOAD ASSETS (Images and Fonts)
# We load all the files we need at the start so the app runs smoothly.
# =================================================================================

# We use a 'try...except' block to prevent the app from crashing if a file is missing.
try:
    # --- FIX: Pre-load all backgrounds for quick switching ---
    # We load both images and store them in a dictionary.
    backgrounds = {
        'bg1': pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg.jpg')).convert(), (WIDTH, HEIGHT)),
        'bg2': pygame.transform.scale(pygame.image.load(os.path.join(assets_dir, 'bg_2.jpeg')).convert(), (WIDTH, HEIGHT))
    }
    # This sets the starting background.
    current_background = backgrounds['bg1']
except FileNotFoundError:
    print("ERROR: A background image is missing from the assets folder!")
    # If an image is missing, we create a plain dark color as a fallback.
    current_background = pygame.Surface((WIDTH, HEIGHT))
    current_background.fill((20, 20, 30))

# --- UI Enhancement: Create a semi-transparent overlay ---
# This Surface will be drawn over the background to make text easier to read.
# pygame.SRCALPHA allows the Surface to have per-pixel transparency.
overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
# We fill it with black (0, 0, 0) and set its alpha (transparency) to 120 (out of 255).
overlay.fill((0, 0, 0, 120))

# --- UI Enhancement: Load custom fonts ---
try:
    # We load our downloaded fonts. The number is the font size in pixels.
    font_bold = pygame.font.Font(os.path.join(fonts_dir, 'Inter-Bold.ttf'), 128)
    font_regular = pygame.font.Font(os.path.join(fonts_dir, 'Inter-Regular.ttf'), 32)
except FileNotFoundError:
    print("Font files not found in assets/fonts/. Using default font.")
    # If the custom fonts are missing, we use Pygame's default font.
    font_bold = pygame.font.Font(None, 150)
    font_regular = pygame.font.Font(None, 40)

# =================================================================================
# 6. HELPER FUNCTION and GAME CLOCK
# A helper function lets us reuse code easily. The clock controls the frame rate.
# =================================================================================

def draw_text_with_shadow(surface, text, font, color, position, shadow_color=(0, 0, 0)):
    """A function to render text with a simple drop shadow for a 3D effect."""
    x, y = position
    # First, we render the text in the shadow color, slightly offset down and to the right.
    shadow_surface = font.render(text, True, shadow_color)
    surface.blit(shadow_surface, (x + 3, y + 3))
    # Then, we render the main text in its actual color directly on top.
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, (x, y))

# The game clock is used to control the speed of our main loop (Frames Per Second).
clock = pygame.time.Clock()

# =================================================================================
# 7. MAIN APPLICATION LOOP
# This is the heart of the program. It runs continuously until the user quits.
# =================================================================================

# This variable controls the loop. When it becomes False, the loop ends.
running = True

while running:
    # --- Event Handling ---
    # Pygame processes all user inputs (mouse, keyboard) as a list of events.
    # We must loop through this list to see what the user is doing.
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        # This event triggers if the user clicks the standard 'X' (if the window has one)
        # or if the system tells the program to close.
        if event.type == pygame.QUIT:
            running = False

        # This event triggers when the user presses any key on the keyboard.
        if event.type == pygame.KEYDOWN:
            # We check which specific key was pressed.
            if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                running = False # Quit if 'Q' or 'Escape' is pressed.
            
            # --- FIX: Re-implementing background switching ---
            if event.key == pygame.K_0:
                print("Switching to background 1")
                current_background = backgrounds['bg1']
            if event.key == pygame.K_1:
                print("Switching to background 2")
                current_background = backgrounds['bg2']

        # --- FIX: Handling clicks for our custom 'X' button ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            # We check if the mouse click was inside the rectangle of our close button.
            if close_button_rect.collidepoint(mouse_pos):
                running = False # If it was, we quit the app.

    # --- Drawing Logic (This happens every single frame) ---
    # The order of drawing is important. Things drawn first are at the bottom.
    
    # 1. Draw the background image first.
    screen.blit(current_background, (0, 0))
    # 2. Draw the dark overlay on top of the background.
    screen.blit(overlay, (0, 0))

    # 3. Get the current time and format it into strings.
    currentTime = datetime.now()
    time_str = currentTime.strftime("%I:%M")
    seconds_str = currentTime.strftime("%S")
    ampm_str = currentTime.strftime("%p")
    date_str = currentTime.strftime("%A, %B %d")

    # 4. Draw the main time (HH:MM).
    time_surface = font_bold.render(time_str, True, (255, 255, 255))
    time_rect = time_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    draw_text_with_shadow(screen, time_str, font_bold, (255, 255, 255), time_rect.topleft)

    # 5. Draw the smoothly blinking colon.
    # We use math.sin() to create a value that smoothly goes from -1 to 1 and back.
    # We adjust this to create an alpha value that goes from 0 (invisible) to 255 (visible).
    colon_alpha = (math.sin(pygame.time.get_ticks() * 0.002) + 1) / 2 * 255
    colon_surface = font_bold.render(":", True, (255, 255, 255))
    colon_surface.set_alpha(colon_alpha) # Apply the calculated transparency.
    colon_rect = colon_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(colon_surface, colon_rect)
    
    # 6. Draw the smaller text (seconds, AM/PM, and date).
    seconds_pos = (time_rect.right + 15, time_rect.centery + 15)
    ampm_pos = (time_rect.right + 15, time_rect.centery - 25)
    date_surface = font_regular.render(date_str, True, (220, 220, 220))
    date_rect = date_surface.get_rect(center=(WIDTH // 2, HEIGHT - 60))

    draw_text_with_shadow(screen, seconds_str, font_regular, (200, 200, 200), seconds_pos)
    draw_text_with_shadow(screen, ampm_str, font_regular, (200, 200, 200), ampm_pos)
    draw_text_with_shadow(screen, date_str, font_regular, (220, 220, 220), date_rect.topleft)
    
    # 7. --- FIX: Draw the custom close button ---
    # We define the button's rectangle and color.
    close_button_rect = pygame.Rect(WIDTH - 40, 10, 30, 30)
    close_button_color = (100, 100, 100) # Default grey color
    
    # If the mouse is hovering over the button's rectangle, we change its color to red.
    if close_button_rect.collidepoint(mouse_pos):
        close_button_color = (255, 0, 0)
        
    pygame.draw.rect(screen, close_button_color, close_button_rect, border_radius=5)
    draw_text_with_shadow(screen, "X", font_regular, (255,255,255), (WIDTH - 33, 8))


    # --- Update the Display ---
    # This command takes everything we've drawn in this frame and shows it on the screen.
    pygame.display.flip()

    # This tells Pygame to wait long enough to keep the loop running at 60 FPS.
    clock.tick(60)

# =================================================================================
# 8. QUIT
# Once the `while running:` loop is finished, we clean up and close the program.
# =================================================================================
pygame.quit()