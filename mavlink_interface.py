
import time
import pymavlink.dialects.v20.common as mavlink
from pymavlink import mavutil

class MAVLinkInterface:
    def __init__(self, port, baudrate=115200):
        self.connection = mavutil.mavlink_connection(port, baud=baudrate)
        self.connection.wait_heartbeat()
        print("[INFO] Verbindung hergestellt!")

    def is_connected(self):
        return self.connection is not None

    def arm(self):
        self.connection.arducopter_arm()
        print("[INFO] Drohne gearmed.")

    def disarm(self):
        self.connection.arducopter_disarm()
        print("[INFO] Drohne disarmed.")

    def motor_test(self, motor, power):
        """ Testet die Motoren mit einer bestimmten Leistung (0-100%). """
        self.connection.mav.command_long_send(
            self.connection.target_system, self.connection.target_component,
            mavlink.MAV_CMD_DO_MOTOR_TEST, 0,
            motor, 0, power, 10, 0, 0, 0
        )
        print(f"[INFO] Motor {motor} auf {power}% gesetzt.")

    def get_param(self, param_name):
        """ Fragt einen bestimmten Parameter ab. """
        self.connection.mav.param_request_read_send(
            self.connection.target_system,
            self.connection.target_component,
            str(param_name).encode(),
            -1
        )

        timeout = time.time() + 2  # Timeout nach 2 Sekunden
        while time.time() < timeout:
            msg = self.connection.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
            if msg and msg.param_id.decode("utf-8") == param_name:
                print(f"[INFO] Parameter {param_name}: {msg.param_value}")
                return msg.param_value

        print(f"[WARN] Parameter {param_name} nicht gefunden!")
        return None

    def get_all_params(self):
        """ Fragt alle Parameter vom Autopiloten ab. """
        params = {}
        self.connection.mav.param_request_list_send(
            self.connection.target_system,
            self.connection.target_component
        )

        timeout = time.time() + 5  # Maximal 5 Sekunden warten
        while time.time() < timeout:
            msg = self.connection.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
            if msg:
                param_name = msg.param_id  # Fix: Kein decode mehr nötig
                param_value = msg.param_value
                params[param_name] = param_value
                print(f"[DEBUG] {param_name}: {param_value}")

        print(f"[INFO] {len(params)} Parameter geladen.")
        return params


    def set_param(self, param_name, value):
        """ Setzt einen Parameter im Autopiloten. """
        self.connection.mav.param_set_send(
            self.connection.target_system,
            self.connection.target_component,
            str(param_name).encode(),
            float(value),
            mavlink.MAV_PARAM_TYPE_REAL32
        )
        print(f"[INFO] Parameter {param_name} auf {value} gesetzt.")

    def get_telemetry(self):
        """ Holt die aktuelle Position und Höhe der Drohne. """
        msg = self.connection.recv_match(type="GLOBAL_POSITION_INT", blocking=False)


        if msg:
            return {
                "lat": msg.lat / 1e7,
                "lon": msg.lon / 1e7,
                "altitude": msg.relative_alt / 1000
            }
        return {}

    def get_log(self):
        """ Holt MAVLink-Logs (Status-Nachrichten). """
        msg = self.connection.recv_match(type="STATUSTEXT", blocking=False)
        if msg:
            return msg.text
        return None
