# serial testing for python


import cv2
import math
import numpy as np
import serial
import time
import os

from pyzbar.pyzbar import decode

global home_on_start
home_on_start = False

global x_max, y_max, z_max
x_max = 0
y_max = 0
z_max = 0

global x_negative, y_negative, z_negative
x_negative = False
y_negative = False
z_negative = False

global x, y, z
x = 0
y = 0
z = 0

file_name = "config.txt"
conversion_rate = 0.05


def move_by_offset(ser, offset_x, offset_y):
    print("Hit Move")
    command = f"G00 X{offset_x} Y{offset_y}"
    send_command(ser, command)

def calculate_offset(qr_coordinates):
    # Calculate the offset between the QR codes center and the frames center
    qr_center_x = sum(point.x for point in qr_coordinates) / 4
    qr_center_y = sum(point.y for point in qr_coordinates) / 4
    frame_center_x = 640 / 2
    frame_center_y = 480 / 2
    offset_x = qr_center_x - frame_center_x
    offset_y = qr_center_y - frame_center_y
    return offset_x, offset_y


def detect_qr_codes(frame):
    decoded_objects = decode(frame)

    if decoded_objects is not None:
        for obj in decoded_objects:
            qr_code_data = obj.data.decode('utf-8')
            qr_code_coordinates = obj.polygon

            return True, qr_code_data, qr_code_coordinates
        return False, None, None


def bounds_comparison(value, max_value, current_value):
    if value is not None:
        temp = current_value + value
        if temp >= max_value:
            return max_value - current_value
        if temp <= 0:
            return 0 - current_value
        else:
            return temp
    return None


def check_bounds(command):
    global x_max, y_max, z_max, x, y, z

    # tracking the G, F, x, y and z values
    g_values = []
    f_value = None
    x_value = None
    y_value = None
    z_value = None

    try:
        # Find all occurrences of 'G'
        g_indices = [i for i, char in enumerate(command) if char == 'G']

        # Iterate through the 'G' indices to extract numeric values
        for i in g_indices:
            value = ''
            j = i + 1
            while j < len(command) and (command[j].isdigit() or command[j] == '-'):
                value += command[j]
                j += 1

            if value:
                g_values.append(int(value))

        # Find and extract other components
        for component in ['X', 'Y', 'Z', 'F']:
            start_index = command.find(component)
            if start_index != -1:
                end_index = start_index + 1
                while end_index < len(command) and (command[end_index].isdigit() or command[end_index] == '-'):
                    end_index += 1

                value = int(command[start_index + 1:end_index])

                if component == 'X':
                    x_value = value
                elif component == 'Y':
                    y_value = value
                elif component == 'Z':
                    z_value = value
                elif component == 'F':
                    f_value = value

        x_value = bounds_comparison(x_value, x_max, x)
        y_value = bounds_comparison(y_value, y_max, y)
        z_value = bounds_comparison(z_value, z_max, z)

        updated_command_parts = []
        if x_value is not None:
            updated_command_parts.append('X{}'.format(x_value))
        if y_value is not None:
            updated_command_parts.append('Y{}'.format(y_value))
        if z_value is not None:
            updated_command_parts.append('Z{}'.format(z_value))
        if f_value is not None:
            updated_command_parts.append('F{}'.format(f_value))
        updated_command = '$J=G{}G{}{}'.format(g_values[0], g_values[1], ''.join(updated_command_parts))

        return updated_command, x_value, y_value, z_value
    except Exception as e:
        print(f"Exception E has been caught: {e}")


def load_config_information(path):
    global x_max, y_max, z_max

    with open(path, 'r') as f:
        line = f.readline()

    parts = line.strip().split(',')
    for part in parts:
        if 'X:' in part:
            x_max = float(part.split(":")[1])
        elif 'Y:' in part:
            y_max = float(part.split(":")[1])
        elif "Z:" in part:
            z_max = float(part.split(":")[1])

    print(x_max, y_max, z_max)


def validate_path(path):
    if os.path.exists(path):
        return "r"
    else:
        return "w"


def check_for_config():
    read_write = validate_path(file_name)

    if read_write == "w":

        print("Hello! It seems like there is no config yet for this machine:")
        machine_x = input("1. Please enter the maximum x steps: ")
        machine_y = input("2. Please enter the maximum y steps: ")
        machine_z = input("3. Please enter the maximum z steps: ")
        print(f"X: {machine_x}, Y: {machine_y}, Z: {machine_z} were the parameters you entered")

        reset_in = input("If the parameters were incorrect please enter: 'reset' "
                         "otherwise enter anything to continue! ")
        if "reset" in reset_in:
            return False
        else:
            with open(file_name, read_write) as f:
                f.write(f"X: {machine_x}, Y: {machine_y}, Z: {machine_z}")

            load_config_information(file_name)
            return True
    elif read_write == "r":
        print("An existing file has been found with the following information:")

        with open(file_name, read_write) as f:
            file_info = f.readlines()
        print(file_info)

        reset_in = input("If the parameters were incorrect please enter: 'reset' "
                         "otherwise enter anything to continue! ")
        if "reset" in reset_in:
            os.remove(file_name)
            return False
        else:
            load_config_information(file_name)
            return True


def parse_jog_command(command):
    global x_negative, y_negative, z_negative
    try:

        command, x_value, y_value, z_value = check_bounds(command)
        print(x_value, y_value, z_value)
        if "X-" in command:
            x_negative = True
        if "Y-" in command:
            y_negative = True
        if "Z-" in command:
            z_negative = True

        return x_value, y_value, z_value, command
    except:
        pass
    return None


def open_serial_port(port, baudrate):
    ser = serial.Serial(port, baudrate, timeout=1)
    if ser.is_open:
        print(f"Connected to {port} at {baudrate} baud")
    else:
        print("Failed to connect")
    return ser


def send_command(ser, command):
    full_command = command + '\r\n'
    ser.write(full_command.encode())
    time.sleep(0.2)
    print(f"Sent: {command}")


def receive_response(ser):
    response = ''
    while True:
        line = ser.readline().decode().strip()
        if not line:
            break
        response += line + '\n'
    return response


def reset_flags():
    global x_negative, y_negative, z_negative
    x_negative = False
    y_negative = False
    z_negative = False


def print_current_location():
    global x, y, z
    print(f"Current location: X: {x}, Y: {y}, Z: {z}\n")


def serial_run():
    global x, y, z, x_negative, y_negative, z_negative, home_on_start
    connection_port = None
    port_list = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "dev/ttyUSB1"]
    baudrate = 115200

    try:
        for port in port_list:
            if os.path.exists(port):
                connection_port = port
                print(connection_port)
                break
    except Exception as e:
        print(f"Caught exception: {e}\n")

    ser = open_serial_port(connection_port, baudrate)
    time.sleep(2)

    config_flag = check_for_config()

    while config_flag is not True:
        config_flag = check_for_config()

    if home_on_start is False:
        print("Initial Startup! Homing on startup...\n")
        send_command(ser, "$H")
        home_on_start = True

    try:
        while True:
            command = input("Enter GRBL command (or 'exit' to quit, or 'help' for more options): ")

            if command.lower() == "exit":
                break

            if command.lower() == "help":
                print("\nAdditional operations include: ")
                # print("1. LOAD FILE: enter 'load' followed by the file path. IE: load /j_code_example.txt")
                print("2. SEARCH: enter 'search' in order to scan the field for a QR code, the position will be stored")
                # print("3. RUN: enter 'run' to use the stored coordinate, position to it\n")

            if command.lower() == "search":
                qr_found = False
                half_max_x = x_max // 2
                # centering x and y
                x = half_max_x
                y = half_max_x

                angle = 0
                step = 1
                acceptable_range = 10
                num_sub_points = 2

                cap = cv2.VideoCapture(1)
                cap.set(cv2.CAP_PROP_FPS, 30)
                if not cap.isOpened():
                    print("Failure to open camera...")
                    continue

                while step < half_max_x and 0 < x < x_max and 0 < y < y_max:
                    ret, frame = cap.read()

                    qr_code_detected, qr_code_data, qr_coordinates = detect_qr_codes(frame)

                    cv2.imshow("Webcam Feed", frame)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                    if qr_code_detected:
                        qr_found = True
                        print("QR Detected!")
                        print("Webcam coordinates of detection: ", qr_coordinates)
                        print("Centering camera...")
                        offset_x, offset_y = calculate_offset(qr_coordinates)
                        print(offset_x, offset_y)

                        if abs(offset_x) <= acceptable_range and abs(offset_y) <= acceptable_range:
                            print("Camera aligned...")
                            break

                        offset_x, offset_y = calculate_offset(qr_coordinates)
                        if not abs(offset_x) <= acceptable_range:
                            move_x = -1 if offset_x > 0 else 1
                        else:
                            move_x = 0

                        if not abs(offset_y) <= acceptable_range:
                            move_y = 1 if offset_y > 0 else -1
                        else:
                            move_y = 0

                        print(move_x, move_y)
                        x += move_x
                        y += move_y
                        move_by_offset(ser, x, y)

                    if not qr_found:
                        angle_radians = math.radians(angle)

                        x += step * math.cos(angle_radians)
                        y += step * math.sin(angle_radians)

                        print("QR not found")
                        angle += 70  # You can adjust the angle increment for different spiral patterns
                        step += 0.5

                        if 0 < x < 400 and 0 < y < 400:
                            test_command = f"G00 X{x} Y{y}"
                            send_command(ser, test_command)

                cap.release()
                cv2.destroyAllWindows()

            if "$H" in command:
                x, y, z = 0.0, 0.0, 0.0
                print("Coordinates reset to (0.000, 0.000, 0.000)")

            # Parse $J command for jogging
            elif "$J=" in command:
                jog_values = parse_jog_command(command)

                if jog_values:
                    dx, dy, dz, command = jog_values
                    print(command)
                    if dx is not None:
                        x += dx
                    if dy is not None:
                        y += dy
                    if dz is not None:
                        z += dz

                    print(f"Jogging: X += {dx}, Y += {dy}, Z += {dz}")
                else:
                    print("Invalid jog command.")

            send_command(ser, command)
            response = receive_response(ser)
            print(f"Response: {response}")
            print_current_location()
            reset_flags()
    except KeyboardInterrupt:
        print("Exiting...")

    ser.close()


if __name__ == "__main__":
    serial_run()

