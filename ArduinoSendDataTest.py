import serial
import time

# 1. SETUP - Change 'COM4' to your actual port from Arduino IDE
PORT = 'COM4' 
BAUD = 115200

try:
    # Open the serial port
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"Connected to {PORT} at {BAUD} baud.")
    
    # CRITICAL: Arduino resets when Serial opens. 
    # We must wait for it to wake up before sending data.
    print("Waiting 2 seconds for Arduino to reset...")
    time.sleep(2)

    # 2. SEND DATA
    test_label = "V"
    test_value = 12.34
    message = f"{test_label}{test_value}\n"
    
    print(f"Sending: {message.strip()}")
    ser.write(message.encode())

    # 3. READ RESPONSE (The Echo)
    # Wait a moment for the Arduino to process and send back
    time.sleep(0.1) 
    
    if ser.in_waiting > 0:
        answer = ser.readline().decode('utf-8').strip()
        print(f"SUCCESS! Arduino says: {answer}")
    else:
        print("No response from Arduino. Check your Echo sketch!")

    # 4. CLEANUP
    ser.close()
    print("Port closed.")

except Exception as e:
    print(f"ERROR: {e}")