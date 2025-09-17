import serial
import json
import time
import threading
import serial.tools.list_ports


ser = None  # Global serial connection


def initialize_COM_port(baudrate=9600, timeout=1):
    global ser
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if (
            "USB" in port.description
            or "USB" in port.hwid
            or "Serial" in port.description
        ):
            ser = serial.Serial(port.device, baudrate=baudrate, timeout=timeout)
            print(f"Connected to {port.device}")
            return True
    print("No USB-Serial device found.")
    return False


def send_to_pi(data):
    global ser
    if ser and ser.is_open:
        if isinstance(data, str):
            data = data.encode("utf-8")
        ser.write(data)
        print("Data sent.")
    else:
        print("Serial connection not initialized.")


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

# initialize_COM_port()

# Configure the DAC:

def config_RIS(daisy_chain_device_num = 0, voltage_range = "0-10V"):
    config_msg = (
        json.dumps(
            {
                "Config": True,
                "daisy_chain_device_num": daisy_chain_device_num,
                "voltage_range": voltage_range,
            }
        )
        + "\n"
    )
    ser.write(config_msg.encode("utf-8"))
    print("Configuration sent:", config_msg)

# Example usage:
# config_RIS(0, "0-10V")


# try:
#     vector = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
#     # vector = [vector, vector] # Used for testing with two DAC Daisychained
#     json_str = json.dumps(vector) + "\n"
#     ser.write(json_str.encode("utf-8"))
#     print("Sent:", vector)
#     # Delay before sending next vector
#     time.sleep(5)
# 
# finally:
#     listening = False  # Stop the listening thread
#     listener_thread.join(timeout=1)  # Wait for thread to finish
#     ser.close()
#     print("Serial connection closed.")
# 