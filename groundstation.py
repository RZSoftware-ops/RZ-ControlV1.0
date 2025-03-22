import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget,
    QGridLayout, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QSlider
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QTimer, Qt
from mavlink_interface import MAVLinkInterface

class GroundStation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.previous_positions = []  # Liste zur Speicherung der letzten Positionen

        self.setWindowTitle("Drone Ground Station")
        self.setGeometry(100, 100, 900, 600)
        self.setWindowIcon(QIcon("logo.png"))

        self.mav = None
        self.connected = False

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tabs
        self.main_tab = QWidget()
        self.setup_main_tab()
        self.tabs.addTab(self.main_tab, "Telemetrie")

        self.param_tab = QWidget()
        self.setup_param_tab()
        self.tabs.addTab(self.param_tab, "Parameter")

        self.motor_test_tab = QWidget()
        self.setup_motor_test_tab()
        self.tabs.addTab(self.motor_test_tab, "Motor Test")

        # Timer für Telemetrie
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.update_telemetry)

    def setup_main_tab(self):
        layout = QVBoxLayout()

        self.logo_label = QLabel(self)
        pixmap = QPixmap("logo.png")
        self.logo_label.setPixmap(pixmap)
        self.logo_label.setScaledContents(True)
        layout.addWidget(self.logo_label)

        self.telemetry_layout = QGridLayout()
        layout.addLayout(self.telemetry_layout)

        self.map_view = QWebEngineView()
        self.map_view.setHtml(open("map.html", "r").read())
        layout.addWidget(self.map_view)

        self.com_port_selector = QComboBox()
        self.com_port_selector.addItems(self.get_available_ports())
        layout.addWidget(self.com_port_selector)

        self.connect_button = QPushButton("Mit Drohne verbinden")
        self.connect_button.clicked.connect(self.connect_drone)
        layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Verbindung trennen")
        self.disconnect_button.clicked.connect(self.disconnect_drone)
        layout.addWidget(self.disconnect_button)

        self.arm_button = QPushButton("Drohne ARMEN")
        self.arm_button.clicked.connect(self.arm_drone)
        layout.addWidget(self.arm_button)

        self.disarm_button = QPushButton("Drohne DISARMEN")
        self.disarm_button.clicked.connect(self.disarm_drone)
        layout.addWidget(self.disarm_button)

        self.telemetry_labels = {
            "Heartbeat": QLabel("❌"),
            "Höhe": QLabel("-- m"),
            "Lat": QLabel("--"),
            "Lon": QLabel("--"),
        }

        for row, (key, label) in enumerate(self.telemetry_labels.items()):
            self.telemetry_layout.addWidget(QLabel(key + ":"), row, 0)
            self.telemetry_layout.addWidget(label, row, 1)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_box)

        self.main_tab.setLayout(layout)

    def setup_param_tab(self):
        layout = QVBoxLayout()

        self.param_table = QTableWidget(0, 2)
        self.param_table.setHorizontalHeaderLabels(["Parameter", "Wert"])
        layout.addWidget(self.param_table)

        self.load_params_button = QPushButton("Lade Parameter")
        self.load_params_button.clicked.connect(self.load_parameters)
        layout.addWidget(self.load_params_button)

        self.save_params_button = QPushButton("Speichern")
        self.save_params_button.clicked.connect(self.save_parameters)
        layout.addWidget(self.save_params_button)

        self.param_tab.setLayout(layout)

    def load_parameters(self):
        if self.mav:
            self.param_table.setRowCount(0)
            params = self.mav.get_all_params()

            for param, value in params.items():
                row_position = self.param_table.rowCount()
                self.param_table.insertRow(row_position)
                self.param_table.setItem(row_position, 0, QTableWidgetItem(param))
                self.param_table.setItem(row_position, 1, QTableWidgetItem(str(value)))

    def save_parameters(self):
        if self.mav:
            for row in range(self.param_table.rowCount()):
                param_name = self.param_table.item(row, 0).text()
                param_value = float(self.param_table.item(row, 1).text())
                self.mav.set_param(param_name, param_value)

            self.disconnect_drone()
            self.connect_drone()

    def setup_motor_test_tab(self):
        layout = QVBoxLayout()
        self.motor_sliders = {}

        for i in range(1, 5):
            label = QLabel(f"Motor {i}")
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(0)
            layout.addWidget(label)
            layout.addWidget(slider)
            self.motor_sliders[i] = slider

        self.start_motor_test_button = QPushButton("Motor-Test Starten")
        self.start_motor_test_button.clicked.connect(self.start_motor_test)
        layout.addWidget(self.start_motor_test_button)

        self.stop_motor_test_button = QPushButton("Motor-Test Stoppen")
        self.stop_motor_test_button.clicked.connect(self.stop_motor_test)
        layout.addWidget(self.stop_motor_test_button)

        self.motor_test_tab.setLayout(layout)

    def start_motor_test(self):
        if self.mav:
            for motor, slider in self.motor_sliders.items():
                power = slider.value()
                self.mav.motor_test(motor, power)

    def stop_motor_test(self):
        if self.mav:
            for motor in self.motor_sliders:
                self.mav.motor_test(motor, 0)

    def arm_drone(self):
        if self.mav:
            self.mav.arm()

    def disarm_drone(self):
        if self.mav:
            self.mav.disarm()

    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect_drone(self):
        selected_port = self.com_port_selector.currentText()
        self.mav = MAVLinkInterface(selected_port, baudrate=115200)

        if self.mav.is_connected():
            self.telemetry_labels["Heartbeat"].setText("✅")
            self.connected = True
            self.telemetry_timer.start(1000)

    def disconnect_drone(self):
        if self.mav:
            self.mav.connection.close()
            self.mav = None
            self.connected = False
            self.telemetry_labels["Heartbeat"].setText("❌ Verbindung getrennt!")
    '''
    def update_telemetry(self):
        if self.connected and self.mav:
            data = self.mav.get_telemetry()
            if data:
                self.telemetry_labels["Höhe"].setText(f"{data.get('altitude', '--')} m")
                self.telemetry_labels["Lat"].setText(str(data.get("lat", "--")))
                self.telemetry_labels["Lon"].setText(str(data.get("lon", "--")))

            log_msg = self.mav.get_log()
            if log_msg:
                self.log_box.append(log_msg)
    '''
    def update_telemetry(self):
        if self.connected and self.mav:
            # Telemetriedaten von der Drohne abrufen
            data = self.mav.get_telemetry()

            # GPS-Position filtern, wenn sie vorhanden ist
            if data:
                lat = data.get("lat")
                lon = data.get("lon")

                # Speichern der letzten Positionen für den gleitenden Durchschnitt
                if lat is not None and lon is not None:
                    self.previous_positions.append((lat, lon))

                    # Nur die letzten 10 Positionen für den Durchschnitt verwenden
                    if len(self.previous_positions) > 10:
                         self.previous_positions.pop(0)

                    # Berechne den gleitenden Durchschnitt
                    avg_lat = sum([pos[0] for pos in self.previous_positions]) / len(self.previous_positions)
                    avg_lon = sum([pos[1] for pos in self.previous_positions]) / len(self.previous_positions)

                    # Update die GUI mit den gefilterten Werten
                    self.telemetry_labels["Lat"].setText(str(avg_lat))
                    self.telemetry_labels["Lon"].setText(str(avg_lon))

                    # Update die Karte mit der gefilterten Position
                    self.update_map(avg_lat, avg_lon)

                # Höhe anzeigen
                self.telemetry_labels["Höhe"].setText(f"{data.get('altitude', '--')} m")

                log_msg = self.mav.get_log()
                if log_msg:
                    self.log_box.append(log_msg)

    def update_map(self, lat, lon):
        # Übergebe die gefilterte Position an die Karte
        script = f'updatePosition({lat}, {lon});'
        self.map_view.page().runJavaScript(script)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GroundStation()
    window.show()
    sys.exit(app.exec())
