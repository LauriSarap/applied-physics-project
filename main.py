import neopixel
from machine import Pin
import time
import ujson
import os
import urandom

# Configuration
PIN_A = 1
PIN_B = 2
LED_NUM_A = 120
LED_NUM_B = 64
BRIGHTNESS = 0.05
HIT_POINT_BRIGHTNESS_BOOST = 10.0
HIT_DISPLAY_DURATION = 500
WAVE_LIGHT_SPREAD_DELAY = 80
WAVE_LIGHT_DURATION = 120
FADE_STEPS = 10
FADE_INTERVAL = 40

# Normal mode delays
NORMAL_MODE_MIN_DELAY = 2  # seconds
NORMAL_MODE_MAX_DELAY = 5  # seconds
# Corner mode delays
CORNER_MODE_MIN_DELAY = 5  # seconds
CORNER_MODE_MAX_DELAY = 10  # seconds


def scale(rgb: tuple, boost: float = 1.0) -> tuple:
    r, g, b = rgb
    factor = BRIGHTNESS * boost
    factor = min(factor, 1.0)
    
    return(
        int(r * factor),
        int(g * factor),
        int(b * factor)
    )

def fill(rgb):
    c = scale(rgb)
    stripA.fill(c)
    stripB.fill(c)
    
    stripA.write()
    stripB.write()

def clear():
    fill((0, 0, 0))

stripA = neopixel.NeoPixel(Pin(PIN_A), LED_NUM_A)
stripB = neopixel.NeoPixel(Pin(PIN_B), LED_NUM_B)


ROWS = 16
COLS = 15

A_ROWS = (ROWS + 1) // 2
B_ROWS = ROWS // 2
LEDS_PER_ACOL = A_ROWS
LEDS_PER_BROW = (COLS + 1) // 2

active_hits = {}
active_vertical_leds = {}


def grid_to_led(location: tuple):
    row, col = location
    if not (0 <= row < ROWS and 0 <= col < COLS):
        raise ValueError("row/col outside matrix")
    
    # Strip A rows
    if row % 2 == 0:
        base = col * LEDS_PER_ACOL
        offset = row // 2

        if col % 2 == 0:
            index = base + offset
        else:
            index = base + (LEDS_PER_ACOL - 1 - offset)
        return ('A', index)
    
    # Strip B rows / holes
    if col % 2 == 1:
        return None

    brow = (row - 1) // 2
    base = brow * LEDS_PER_BROW
    offset = col // 2

    if brow % 2 == 0:
        index = base + offset
    else:
        index = base + (LEDS_PER_BROW - 1 - offset)
    return ('B', index)
    

def set_pixel(location: tuple, rgb: tuple, boost: float = 1.0, *, auto_write: bool = True):
    mapping = grid_to_led(location)
    if mapping is None:
        return # Hit a hole
    
    strip, index = mapping
    if strip == 'A':
        stripA[index] = scale(rgb, boost)
    else:
        stripB[index] = scale(rgb, boost)
    
    if auto_write:
        stripA.write()
        stripB.write()


def start_fade_animation(now, hit_points, vertical_points):
    for row, col, color in hit_points:
        start_fade_time = now + 100
        active_hits[(row, col)] = (color, start_fade_time)
    
    for row, col, color in vertical_points:
        start_fade_time = now + 50
        active_vertical_leds[(row, col)] = (color, start_fade_time)


def process_active_points():
    global active_hits, active_vertical_leds
    
    now = time.ticks_ms()
    
    hit_points_to_remove = []
    for (row, col), (color, start_fade_time) in active_hits.items():
        if time.ticks_diff(now, start_fade_time) >= 0:
            elapsed = time.ticks_diff(now, start_fade_time)
            fade_progress = min(1.0, elapsed / (FADE_STEPS * FADE_INTERVAL))
            
            if fade_progress >= 1.0:
                set_pixel((row, col), (0, 0, 0))
                hit_points_to_remove.append((row, col))
            else:
                fade_factor = 1.0 - fade_progress
                r, g, b = color
                boost_factor = min(fade_factor * HIT_POINT_BRIGHTNESS_BOOST, 1.0)
                boosted_color = (
                    int(r * boost_factor),
                    int(g * boost_factor),
                    int(b * boost_factor)
                )
                set_pixel((row, col), boosted_color)
    
    for point in hit_points_to_remove:
        if point in active_hits:
            del active_hits[point]
    
    vertical_leds_to_remove = []
    for (row, col), (color, start_fade_time) in active_vertical_leds.items():
        if time.ticks_diff(now, start_fade_time) >= 0:
            elapsed = time.ticks_diff(now, start_fade_time)
            fade_progress = min(1.0, elapsed / (FADE_STEPS * FADE_INTERVAL))
            
            if fade_progress >= 1.0:
                set_pixel((row, col), (0, 0, 0))
                vertical_leds_to_remove.append((row, col))
            else:
                fade_factor = 1.0 - fade_progress
                r, g, b = color
                faded_color = (
                    int(r * fade_factor),
                    int(g * fade_factor),
                    int(b * fade_factor)
                )
                set_pixel((row, col), faded_color)
    
    for point in vertical_leds_to_remove:
        if point in active_vertical_leds:
            del active_vertical_leds[point]


def display_hit_effect(row, col, color):
    vertical_leds = []
    
    above_row = row - 1
    while above_row >= 0:
        mapping = grid_to_led((above_row, col))
        if mapping is not None:
            vertical_leds.append((above_row, col, color))
            break
        above_row -= 1
    
    below_row = row + 1
    while below_row < ROWS:
        mapping = grid_to_led((below_row, col))
        if mapping is not None:
            vertical_leds.append((below_row, col, color))
            break
        below_row += 1
    
    set_pixel((row, col), color, HIT_POINT_BRIGHTNESS_BOOST)
    for vr, vc, vc_color in vertical_leds:
        set_pixel((vr, vc), vc_color)
    
    now = time.ticks_ms()
    hit_points = [(row, col, color)]
    start_fade_animation(now, hit_points, vertical_leds)

    # Wave animation logic
    
    right_boundary = COLS - 1
    left_boundary = 0
    
    active_wave_pixels = []
    
    steps_to_right = right_boundary - col
    steps_to_left = col - left_boundary
    max_steps = max(steps_to_right, steps_to_left)

    for step in range(1, max_steps + 1):
        process_active_points()
        now = time.ticks_ms()
        
        # Left wave
        left_col = col - step
        if left_col >= left_boundary:
            set_pixel((row, left_col), color)
            turn_off_time = now + WAVE_LIGHT_DURATION
            active_wave_pixels.append((left_col, turn_off_time))
        
        # Right wave
        right_col = col + step
        if right_col <= right_boundary:
            set_pixel((row, right_col), color)
            turn_off_time = now + WAVE_LIGHT_DURATION
            active_wave_pixels.append((right_col, turn_off_time))
        
        
        i = 0
        while i < len(active_wave_pixels):
            wave_col, off_time = active_wave_pixels[i]
            if time.ticks_diff(now, off_time) >= 0:
                set_pixel((row, wave_col), (0, 0, 0), auto_write=False)
                active_wave_pixels.pop(i)
            else:
                i += 1
        
        stripA.write()
        stripB.write()
        time.sleep_ms(WAVE_LIGHT_SPREAD_DELAY)
        
        if left_col < left_boundary and right_col > right_boundary:
            break
    
    # Reflection wave - from right to left
    current_col = right_boundary
    while current_col >= left_boundary:
        process_active_points()
        now = time.ticks_ms()
        
        if current_col != col:
            set_pixel((row, current_col), color)
            turn_off_time = now + WAVE_LIGHT_DURATION
            active_wave_pixels.append((current_col, turn_off_time))
        
        i = 0
        while i < len(active_wave_pixels):
            wave_col, off_time = active_wave_pixels[i]
            if time.ticks_diff(now, off_time) >= 0:
                set_pixel((row, wave_col), (0, 0, 0), auto_write=False)
                active_wave_pixels.pop(i)
            else:
                i += 1
        
        stripA.write()
        stripB.write()
        time.sleep_ms(WAVE_LIGHT_SPREAD_DELAY)
        current_col -= 1
    
    for c in range(COLS):
        if c != col:
            set_pixel((row, c), (0, 0, 0), auto_write=False)
    
    stripA.write()
    stripB.write()


def play_visualization(hits, is_in_corner=False):
    global active_hits, active_vertical_leds
    
    active_hits = {}
    active_vertical_leds = {}
    
    if not hits:
        return
    
    processed_hits = []
    current_time = 0
    
    # Valime osakeste vahe vastavalt sellele, kas visualiseering asub detektori nurgas või keskel
    # Jätame andmete ajafaktori täiesti välja, sest niimoodi sai visuaalselt parima tulemuse.
    if is_in_corner:
        min_delay = CORNER_MODE_MIN_DELAY
        max_delay = CORNER_MODE_MAX_DELAY
    else:
        min_delay = NORMAL_MODE_MIN_DELAY
        max_delay = NORMAL_MODE_MAX_DELAY
    
    for hit in hits:
        if len(hit) < 4:
            continue
            
        _, row, col, color = hit
        
        random_delay = urandom.uniform(min_delay, max_delay) * 1000
        current_time += random_delay
        
        processed_hits.append([current_time, row, col, color])
    
    start_ms = time.ticks_ms()
    next_index = 0
    
    while next_index < len(processed_hits) or active_hits or active_vertical_leds:
        now = time.ticks_ms()
        
        process_active_points()
        
        while next_index < len(processed_hits) and time.ticks_diff(now, start_ms) >= processed_hits[next_index][0]:
            t_hit, row, col, color = processed_hits[next_index]
            
            display_hit_effect(row, col, color)
            
            next_index += 1
        
        time.sleep_ms(5)

    clear()


def play_hits(filename="hits.json", is_in_corner=False):
    if filename not in os.listdir():
        raise OSError(f"{filename} not found on Pico flash")

    hits = ujson.load(open(filename))
    play_visualization(hits, is_in_corner)

try:
    clear()

    # NB! Siia oleks vaja nupu loogikat, et
    # nad ei peaks ise scripti muutma, et režiimi vahetada

    play_hits(is_in_corner=True)
finally:
    clear()
    
