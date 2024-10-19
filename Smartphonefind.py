import bluetooth
from picrawler import Picrawler
from robot_hat import TTS, Music, Ultrasonic
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
import time
import math
from collections import deque

# Initialize components
crawler = Picrawler()
tts = TTS()
music = Music()
sonar = Ultrasonic(Pin("D2"), Pin("D3"))

# OLED display setup
serial = i2c(port=1, address=0x3C)
oled = ssd1306(serial)

# Bluetooth MAC address of your phone
phone_mac_address = "20:20:08:59:27:13"

# Store the last 5 RSSI values for smoothing
rssi_values = deque(maxlen=5)

def smooth_rssi(rssi):
    rssi_values.append(rssi)
    return sum(rssi_values) / len(rssi_values)

# Function to find the phone by signal using PyBluez
def find_phone_classic():
    try:
        rssi_values = []
        for _ in range(3):  # Perform 3 scans
            devices = bluetooth.discover_devices(duration=2, lookup_names=True, flush_cache=True)
            for addr, name in devices:
                if addr.lower() == phone_mac_address.lower():
                    rssi_values.append(device.rssi)
        if rssi_values:
            avg_rssi = sum(rssi_values) / len(rssi_values)
            print("Phone detected with average RSSI:", avg_rssi)
            return avg_rssi
        print("Phone not detected.")
    except Exception as e:
        print(f"Bluetooth scanning error: {e}")
    return None

# Function to draw the circle, needle, and RSSI value
def draw_needle(angle, rssi=None):
    with canvas(oled) as draw:
        center_x, center_y = 64, 32
        radius = 30
        # Draw circle
        draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline="white")
        # Draw needle
        end_x = center_x + int(radius * math.cos(math.radians(angle)))
        end_y = center_y + int(radius * math.sin(math.radians(angle)))
        draw.line((center_x, center_y, end_x, end_y), fill="white")
        # Display RSSI value in the center if provided
        if rssi is not None:
            draw.text((center_x - 10, center_y - 5), f"{rssi}", fill="white")

# Function to calculate angle based on RSSI
def calculate_angle(rssi):
    max_rssi = -30  # Example value for strongest signal
    min_rssi = -90  # Example value for weakest signal
    angle = 180 * (rssi - min_rssi) / (max_rssi - min_rssi)
    return max(0, min(180, angle))

# Main function
def main():
    speed = 80
    previous_rssi = None
    last_turn_direction = None  # Store the last turn direction
    current_heading = 0  # 0 degrees represents 12 o'clock

    while True:
        try:
            # Scan for the phone
            rssi = find_phone_classic()
            if rssi is not None:
                smoothed_rssi = smooth_rssi(rssi)
                angle = calculate_angle(smoothed_rssi)
                
                if previous_rssi is not None:
                    if smoothed_rssi > previous_rssi:
                        print("Signal stronger. Continuing forward.")
                        tts.say("Signal stronger. Continuing forward.")
                        for _ in range(3):  # Take three steps forward
                            crawler.do_action('forward', 1, speed)
                            distance = sonar.read()
                            if distance > 0 and distance <= 15:
                                print("Obstacle detected! Avoiding...")
                                tts.say("Obstacle detected! Avoiding...")
                                crawler.do_action('turn right', 1, speed)
                                last_turn_direction = 'right'
                                current_heading = (current_heading + 90) % 360
                                break
                        draw_needle(current_heading, smoothed_rssi)  # Update needle to current heading with RSSI
                    elif smoothed_rssi < previous_rssi:
                        print("Signal weaker. Turning to find stronger signal.")
                        tts.say("Signal weaker. Turning to find stronger signal.")
                        crawler.do_action('turn left', 1, speed)
                        last_turn_direction = 'left'
                        current_heading = (current_heading - 90) % 360
                        draw_needle(current_heading)  # Update needle direction
                    else:
                        print("Signal unchanged. Adjusting direction.")
                        tts.say("Signal unchanged. Adjusting direction.")
                        crawler.do_action('turn right', 1, speed)
                        last_turn_direction = 'right'
                        current_heading = (current_heading + 90) % 360
                        draw_needle(current_heading)  # Update needle direction
                
                previous_rssi = smoothed_rssi
            else:
                print("Phone not detected. Scanning...")
                tts.say("Phone not detected. Scanning...")
                crawler.do_action('turn left', 1, speed)
                last_turn_direction = 'left'
                current_heading = (current_heading - 90) % 360
                draw_needle(current_heading)  # Update needle direction
            
            # After avoiding an obstacle, resume the original direction
            if last_turn_direction == 'right':
                crawler.do_action('turn left', 1, speed)
                current_heading = (current_heading - 90) % 360
            elif last_turn_direction == 'left':
                crawler.do_action('turn right', 1, speed)
                current_heading = (current_heading + 90) % 360
            
        except Exception as e:
            print(f"An error occurred: {e}")
            tts.say("An error occurred.")
        time.sleep(2)  # Blocking sleep

if __name__ == "__main__":
    main()
