import serial
import json
import time
import threading

# Define the vectors
vectors = [
    # [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 5.0, 7.8, 0.0, 5.0, 7.8, 0.0, 5.0, 7.8], #phi=-50, theta= 00
    [7.9, 6.0, 4.7, 5.7, 4.6, 1.1, 4.3, 0.1, 8.0], #phi= 50, theta=-45
    [8.0, 0.1, 4.3, 1.1, 4.6, 5.7, 4.7, 6.0, 7.9], #phi= 50, theta= 45
    [7.8, 5.0, 0.0, 7.8, 5.0, 0.0, 7.8, 5.0, 0.0], #phi= 50, theta= 00
    [6.0, 6.0, 6.0, 4.8, 4.8, 4.8, 0.0, 0.0, 0.0], #phi= 00, theta= 45 ?
    [0.0, 0.0, 0.0, 4.8, 4.8, 4.8, 6.0, 6.0, 6.0], #phi= 00, theta=-45 ?
    # [3.3, 2.7, 1.8, 0.0, 5.0, 1.2, 1.5, 2.0, 3.0],
    # [1.0, 2.0, 3.0, 4.0, 5.0, 4.0, 3.0, 2.0, 1.0],
    # [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    # [5.0, 4.5, 3.5, 2.5, 1.5, 1.0, 0.5, 0.0, 0.0],
    # [9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
    # [2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8],
    # [1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7],
    # [4.0, 3.8, 3.6, 3.4, 3.2, 3.0, 2.8, 2.6, 2.4],
    # [0.9, 1.8, 2.7, 3.6, 4.5, 5.4, 6.3, 7.2, 8.1],
    # [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0],
    # [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    # [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Optional: terminates DAC_Controller_PI
]

# Adjust the port depending on your system
ser = serial.Serial("COM4", 9600)
time.sleep(2)  # Let the port initialize

# Flag to control the listening thread
listening = True


def listen_for_responses():
    """Continuously listen for incoming messages from the Pi"""
    global listening
    while listening:
        try:
            if ser.in_waiting > 0:
                response = ser.readline().decode("utf-8").strip()
                if response:
                    print("Received from Pi:", response)
        except Exception as e:
            print(f"Error reading from serial: {e}")
            break
        time.sleep(0.01)  # Small delay to prevent excessive CPU usage


# Start the listening thread
listener_thread = threading.Thread(target=listen_for_responses, daemon=True)
listener_thread.start()


# Configure the DAC:

config_msg = (
    json.dumps(
        {
            "Config": True,
            "daisy_chain_device_num": 0,
            "voltage_range": "0-10V",
        }
    )
    + "\n"
)
ser.write(config_msg.encode("utf-8"))
print("Configuration sent:", config_msg)


try:
    for vector in vectors:
        # vector = [vector, vector] # Used for testing with two DAC Daisychained
        json_str = json.dumps(vector) + "\n"
        ser.write(json_str.encode("utf-8"))
        print("Sent:", vector)

        # Delay before sending next vector
        time.sleep(5)

finally:
    listening = False  # Stop the listening thread
    listener_thread.join(timeout=1)  # Wait for thread to finish
    ser.close()
    print("Serial connection closed.")
