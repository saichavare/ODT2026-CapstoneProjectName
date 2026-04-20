from machine import Pin, PWM, TouchPad
import time
import neopixel

# RGB SENSOR PINS
S0 = Pin(33, Pin.OUT)
S1 = Pin(5, Pin.OUT)
S2 = Pin(19, Pin.OUT)
S3 = Pin(32, Pin.OUT)
OUT = Pin(18, Pin.IN)

S0.value(1)
S1.value(0)  # frequency scaling (leave as is)

# NEOPIXEL SETUP
NUM_PIXELS = 16
np = neopixel.NeoPixel(Pin(22, Pin.OUT), NUM_PIXELS)

# SERVOS
leftservo = PWM(Pin(23), freq=50)   # eye servo
servo = PWM(Pin(13), freq=50)       # touch servo

# SENSORS
eyeleft = Pin(15, Pin.IN, Pin.PULL_UP)
touch = TouchPad(Pin(14))

# READ FREQUENCY FROM COLOR SENSOR
def read_frequency(duration_ms=100):
    count = 0
    end = time.ticks_add(time.ticks_ms(), duration_ms)
    last = OUT.value()

    while time.ticks_diff(end, time.ticks_ms()) > 0:
        current = OUT.value()
        if last == 1 and current == 0:
            count += 1
        last = current

    return count

# READ RGB VALUES (AVERAGED)
def stable_read(samples=5):
    r_total = 0
    g_total = 0
    b_total = 0

    for _ in range(samples):

        S2.value(0); S3.value(0)  # red
        time.sleep_ms(10)
        r_total += read_frequency()

        S2.value(1); S3.value(1)  # green
        time.sleep_ms(10)
        g_total += read_frequency()

        S2.value(0); S3.value(1)  # blue
        time.sleep_ms(10)
        b_total += read_frequency()

    return r_total // samples, g_total // samples, b_total // samples

# MAP SENSOR VALUES TO 0–255
def map_value(val, min_v, max_v):
    mapped = int((val - min_v) * 255 / (max_v - min_v))
    return max(0, min(255, mapped))

# SET ALL LEDS
def set_all(r, g, b):
    for i in range(NUM_PIXELS):
        np[i] = (r, g, b)
    np.write()

# COLOR MATCHING
COLOR_MAP = [
    ("Red", 255, 0, 0),
    ("Green", 0, 255, 0),
    ("Blue", 0, 0, 255),
    ("Yellow", 255, 255, 0),
    ("Orange", 255, 140, 0),
    ("Purple", 148, 0, 211),
    ("Pink", 255, 105, 180),
    ("Cyan", 0, 255, 255),
    ("White", 255, 255, 255),
    ("Black", 0, 0, 0),
    ("Brown", 101, 67, 33),
]

def get_color_name(r, g, b):
    best_name = "Unknown"
    best_distance = float('inf')

    for name, cr, cg, cb in COLOR_MAP:
        distance = ((r - cr)**2 + (g - cg)**2 + (b - cb)**2) ** 0.5
        if distance < best_distance:
            best_distance = distance
            best_name = name

    return best_name, int(best_distance)

# CALIBRATION VALUES
R_MIN, R_MAX = 126, 1167
G_MIN, G_MAX = 120, 891
B_MIN, B_MAX = 164, 1120

# INITIAL STATE
set_all(255, 255, 255)
print("Ready")

current_r, current_g, current_b = 255, 255, 255

THRESHOLD = 25
CONFIRM_COUNT = 3

pending_r, pending_g, pending_b = 255, 255, 255
confirm = 0

# MAIN LOOP
while True:

    # TOUCH SENSOR
    if touch.read() < 200:
        servo.duty(35)
        time.sleep(0.75)
        servo.duty(110)
        time.sleep(0.75)
        print("Touch detected")

    # EYE SENSOR
    if eyeleft.value() == 0:
        leftservo.duty(70)
    else:
        leftservo.duty(110)

    # RGB SENSOR
    r_raw, g_raw, b_raw = stable_read(samples=5)

    r = map_value(r_raw, R_MIN, R_MAX)
    g = map_value(g_raw, G_MIN, G_MAX)
    b = map_value(b_raw, B_MIN, B_MAX)

    # CHECK FOR CHANGE
    if (abs(r - current_r) > THRESHOLD or
        abs(g - current_g) > THRESHOLD or
        abs(b - current_b) > THRESHOLD):

        if (abs(r - pending_r) < THRESHOLD and
            abs(g - pending_g) < THRESHOLD and
            abs(b - pending_b) < THRESHOLD):
            confirm += 1
        else:
            confirm = 1
            pending_r, pending_g, pending_b = r, g, b

        if confirm >= CONFIRM_COUNT:
            set_all(r, g, b)

            current_r, current_g, current_b = r, g, b
            confirm = 0

            name, distance = get_color_name(r, g, b)

            if distance < 80:
                confidence = "High"
            elif distance < 150:
                confidence = "Medium"
            else:
                confidence = "Low"

            print("Color:", name)
            print("RGB:", (r, g, b))
            print("Confidence:", confidence)

    else:
        confirm = 0
        pending_r, pending_g, pending_b = current_r, current_g, current_b

    time.sleep_ms(200)
