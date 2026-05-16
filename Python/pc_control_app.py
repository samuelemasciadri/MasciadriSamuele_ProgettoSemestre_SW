import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import csv
import re
from datetime import datetime
BAUDRATE = 9600

class STM32ControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Control Panel")
        self.serial_port = None
        self.reader_running = False
        self.csv_file = None
        self.csv_writer = None

        self.port_var = tk.StringVar()

        self.build_ui()
        self.refresh_ports()

    def build_ui(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="COM Port:").pack(side="left")

        self.port_combo = ttk.Combobox(top_frame, textvariable=self.port_var, width=15)
        self.port_combo.pack(side="left", padx=5)

        ttk.Button(top_frame, text="Refresh", command=self.refresh_ports).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Connect", command=self.connect).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Disconnect", command=self.disconnect).pack(side="left", padx=5)

        command_frame = ttk.LabelFrame(self.root, text="Commands", padding=10)
        command_frame.pack(fill="x", padx=10, pady=5)

        commands = [
            ("Help", "help"),
            ("Read TMP126", "readSPI_TMP"),
            ("Read TMP ID", "readTMP_ID"),
            ("Read ADC", "readADC"),
            ("Stream ADC ON", "streamADC_on"),
            ("Stream ADC OFF", "streamADC_off"),
            ("Scan I2C", "scanI2C"),
            ("Read I2C", "readI2C"),
            ("I2C HIGH", "writeI2C_high"),
            ("I2C LOW", "writeI2C_low"),
            ("I2C Toggle", "toggleI2C"),
            ("Red ON", "redLED_on"),
            ("Red OFF", "redLED_off"),
            ("Green ON", "greenLED_on"),
            ("Green OFF", "greenLED_off"),
            ("Yellow ON", "yellowLED_on"),
            ("Yellow OFF", "yellowLED_off"),
            ("Toggle LEDs", "toggleLEDs"),
        ]

        for index, (label, command) in enumerate(commands):
            button = ttk.Button(
                command_frame,
                text=label,
                command=lambda cmd=command: self.send_command(cmd)
            )
            button.grid(row=index // 4, column=index % 4, padx=5, pady=5, sticky="ew")

        manual_frame = ttk.Frame(self.root, padding=10)
        manual_frame.pack(fill="x")

        self.manual_entry = ttk.Entry(manual_frame)
        self.manual_entry.pack(side="left", fill="x", expand=True)
        self.manual_entry.bind("<Return>", lambda event: self.send_manual_command())

        ttk.Button(manual_frame, text="Send", command=self.send_manual_command).pack(side="left", padx=5)

        output_frame = ttk.LabelFrame(self.root, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.output_text = scrolledtext.ScrolledText(output_frame, height=18)
        self.output_text.pack(fill="both", expand=True)

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        self.port_combo["values"] = port_names

        if port_names and not self.port_var.get():
            self.port_var.set(port_names[0])

    def connect(self):
        if self.serial_port and self.serial_port.is_open:
            self.log("Already connected.\n")
            return

        port = self.port_var.get()

        if not port:
            messagebox.showerror("Error", "Select a COM port.")
            return

        try:
            self.serial_port = serial.Serial(port, BAUDRATE, timeout=0.1)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stm32_log_{timestamp}.csv"

            self.csv_file = open(filename, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)

            self.csv_writer.writerow([
                "timestamp",
                "source",
                "raw",
                "voltage_mv",
                "temperature_c",
                "value_hex",
                "int_pin",
                "line"
            ])

            self.reader_running = True

            reader_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
            reader_thread.start()

            self.log(f"Connected to {port} at {BAUDRATE} baud.\n")
            self.log(f"Logging to {filename}\n")

        except serial.SerialException as error:
            messagebox.showerror("Serial error", str(error))

    def disconnect(self):
        self.reader_running = False

        if self.serial_port:
            try:
                self.serial_port.close()
            except serial.SerialException:
                pass

        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None

        self.log("Disconnected.\n")

    def send_command(self, command):
        if not self.serial_port or not self.serial_port.is_open:
            self.log("Not connected.\n")
            return

        message = command + "\r\n"

        try:
            self.serial_port.write(message.encode("ascii"))
            self.log(f"> {command}\n")
        except serial.SerialException as error:
            self.log(f"Serial write error: {error}\n")

    def send_manual_command(self):
        command = self.manual_entry.get().strip()

        if command:
            self.send_command(command)
            self.manual_entry.delete(0, tk.END)

    def read_serial_loop(self):
        while self.reader_running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    line = self.serial_port.readline()

                    if line:
                        text = line.decode("ascii", errors="replace")
                        self.save_measurement_to_csv(text)
                        self.root.after(0, self.log, text)

            except serial.SerialException as error:
                self.root.after(0, self.log, f"Serial read error: {error}\n")
                self.reader_running = False

    def save_measurement_to_csv(self, line):
        if not self.csv_writer:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        clean_line = line.strip()

        source = ""
        raw = ""
        voltage_mv = ""
        temperature_c = ""
        value_hex = ""
        int_pin = ""

        tmp_match = re.search(
            r"TMP126 raw=0x([0-9A-Fa-f]+), temp=([+-]?\d+\.\d+) C",
            clean_line
        )

        adc_match = re.search(
            r"ADC raw=(\d+), voltage=(\d+) mV, LM235=([+-]?\d+\.\d+) C",
            clean_line
        )

        i2c_match = re.search(
            r"PCF8575 input = 0x([0-9A-Fa-f]+), INT=(\d+)",
            clean_line
        )

        if tmp_match:
            source = "TMP126"
            raw = "0x" + tmp_match.group(1)
            temperature_c = tmp_match.group(2)

        elif adc_match:
            source = "LM235_ADC"
            raw = adc_match.group(1)
            voltage_mv = adc_match.group(2)
            temperature_c = adc_match.group(3)

        elif i2c_match:
            source = "PCF8575"
            value_hex = "0x" + i2c_match.group(1)
            int_pin = i2c_match.group(2)

        else:
            source = "UART"

        self.csv_writer.writerow([
            timestamp,
            source,
            raw,
            voltage_mv,
            temperature_c,
            value_hex,
            int_pin,
            clean_line
        ])

        self.csv_file.flush()

    def log(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = STM32ControlApp(root)
    root.geometry("850x550")
    root.mainloop()