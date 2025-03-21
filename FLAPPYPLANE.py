import bluetooth
from hid_services import Keyboard
from time import sleep, time
from machine import Pin, I2C
from MPU6050 import accel

# Initialize Bluetooth Keyboard
ble = bluetooth.BLE()
kb = Keyboard("ESP32 Keyboard")
kb.start()
kb.start_advertising()

print("Waiting for Bluetooth connection...")
while not kb.is_connected():
    sleep(1)

print("✅ Connected!")

# Initialize MPU6050 (I2C)
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
mpu = accel(i2c)

# Baseline for tilt detection (use running average)
baseline_y = mpu.get_values()["AcY"]
threshold = 5000  # Adjust sensitivity

# Adaptive cooldown settings
last_jump_time = time()  # Track last jump time
min_cooldown = 0.2       # Minimum time between jumps (rapid taps)
max_cooldown = 1.0       # Maximum cooldown (prevents spam)
cooldown_time = min_cooldown  # Start with the minimum cooldown

# Function to send a spacebar keystroke
def send_spacebar():
    print("🚀 Sending spacebar keystroke...")
    kb.set_keys(0x2C)  # HID keycode for Spacebar
    kb.notify_hid_report()
    sleep(0.1)
    kb.set_keys(0x00)  # Release key
    kb.notify_hid_report()
    sleep(0.1)

# Function to detect tilt movement with adaptive cooldown
def detect_tilt():
    global mpu, baseline_y, last_jump_time, cooldown_time

    try:
        accel_data = mpu.get_values()
        y_accel = accel_data["AcY"]

        current_time = time()
        time_since_last_jump = current_time - last_jump_time

        # Adjust cooldown adaptively
        if time_since_last_jump > max_cooldown:
            cooldown_time = min_cooldown  # Reduce cooldown for better response

        # Prevent rapid spacebar presses
        if time_since_last_jump < cooldown_time:
            return "NO_JUMP"

        # Detect jump and reset cooldown
        if y_accel - baseline_y < -threshold:
            last_jump_time = current_time
            cooldown_time = min(max_cooldown, cooldown_time + 0.1)  # Increase cooldown slightly after a jump
            return "JUMP"

        # Slowly adjust baseline to prevent drift
        baseline_y = (baseline_y * 0.95) + (y_accel * 0.05)

        return "NO_JUMP"

    except OSError as e:
        print("I2C Read Error:", e)
        print("Resetting I2C and MPU6050...")
        i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)  # Reset I2C
        mpu = accel(i2c)  # Reinitialize MPU6050
        return "ERROR"

# Main loop
while True:
    action = detect_tilt()

    if action == "JUMP":
        send_spacebar()  # Send spacebar when JUMP is detected

    sleep(0.1)  # Keep a small delay for responsiveness

