import pygame
from datetime import datetime
import os
import requests
import json

# --------------------------
# Initialize Pygame
# --------------------------
pygame.init()

# Window size
WIDTH, HEIGHT = 600, 600
background = pygame.image.load("../assets/bg.jpg")
background = pygame.transform.scale(background,(WIDTH, HEIGHT))

weather_api = os.getenv("Weather_API_Key")
weather_url = f"http://api.weatherapi.com/v1/current.json?key={weather_api}&q=Dhaka&aqi=yes"
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trife")

# Clock for controlling FPS
clock = pygame.time.Clock()

# --------------------------
# Function to draw digital clock
# --------------------------
def digitalClock(screen, blink):
    currentTime = datetime.now()

    # Use colons when blinking is ON, otherwise spaces
    if blink:
        time_str = currentTime.strftime("%I:%M:%S %p")
    else:
        time_str = currentTime.strftime("%I %M %S %p")

    # Font and color
    font = pygame.font.Font(None, 120)
    weather_font = pygame.font.Font(None, 35)
    text = font.render(time_str, True, (255, 255, 255))
    temporary = "Dhaka, Bangladesh"
    location_text = weather_font.render(temporary, True, (255,255,255))
    location_rect = location_text.get_rect()
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    # Draw text on screen
    screen.blit(text, text_rect)
    screen.blit(location_text, location_rect)

# --------------------------
# Main Loop
# --------------------------
running = True
blink = True
blinkTime = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                running = False
            elif event.key == pygame.K_0:
                background = pygame.image.load("../assets/bg.jpg")
                background = pygame.transform.scale(background, (WIDTH, HEIGHT))
            elif event.key == pygame.K_1:
                background = pygame.image.load("../assets/bg_2.jpeg")
                background = pygame.transform.scale(background, (WIDTH, HEIGHT))
                
    screen.blit(background, (0, 0))
    # screen.blit(weather, (50, 50))
    # Add elapsed time
    blinkTime += clock.get_time()

    # Toggle colon every 3 seconds
    if blinkTime > 440:
        blink = not blink
        blinkTime = 0 # reset timer

    # Draw the digital clock
    digitalClock(screen, blink)

    # Refresh screen
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
