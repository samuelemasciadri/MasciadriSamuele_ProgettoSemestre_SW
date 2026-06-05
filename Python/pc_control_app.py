import csv
import re
import threading
from collections import deque
from datetime import datetime

import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


BAUDRATE = 9600
MAX_GRAPH_POINTS = 200


class STM32ControlApp:
    """PC control panel for the STM32 project.

    The application communicates with the firmware through a serial COM port.
    The same GUI works with USART through an external adapter or with USB CDC,
    because both appear as serial ports on the PC.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Control Panel")
        self.root.minsize(1180, 760)

        self.serial_port = None
        self.reader_running = False
        self.csv_file = None
        self.csv_writer = None

        self.port_var = tk.StringVar()
        self.p0_var = tk.StringVar(value="FF")
        self.p1_var = tk.StringVar(value="FF")
        self.pwm_var = tk.StringVar(value="50")

        self.lm235_times = deque(maxlen=MAX_GRAPH_POINTS)
        self.lm235_temps = deque(maxlen=MAX_GRAPH_POINTS)
        self.tmp126_times = deque(maxlen=MAX_GRAPH_POINTS)
        self.tmp126_temps = deque(maxlen=MAX_GRAPH_POINTS)
        self.sample_index = 0

        self.last_lm235_var = tk.StringVar(value="-- °C")
        self.last_tmp126_var = tk.StringVar(value="-- °C")
        self.last_adc_var = tk.StringVar(value="--")
        self.last_voltage_var = tk.StringVar(value="-- mV")
        self.last_gpio_var = tk.StringVar(value="--")
        self.last_pwm_var = tk.StringVar(value="-- %")
        self.connection_var = tk.StringVar(value="Disconnected")

        self.build_ui()
        self.refresh_ports()

    # -------------------------------------------------------------------------
    # GUI construction
    # -------------------------------------------------------------------------
    def build_ui(self):
        self.configure_style()

        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))

        title = ttk.Label(header, text="STM32 Control Panel", style="Title.TLabel")
        title.pack(side="left")

        status = ttk.Label(header, textvariable=self.connection_var, style="Status.TLabel")
        status.pack(side="right")

        self.build_connection_frame(main)

        body = ttk.PanedWindow(main, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(10, 0))

        left_panel = ttk.Frame(body)
        right_panel = ttk.Frame(body)
        body.add(left_panel, weight=1)
        body.add(right_panel, weight=2)

        self.build_command_notebook(left_panel)
        self.build_measurement_cards(left_panel)
        self.build_graphs(right_panel)
        self.build_output(right_panel)

    def configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Card.TLabelframe", padding=8)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Command.TButton", padding=6)
        style.configure("Accent.TButton", padding=6, font=("Segoe UI", 9, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 13, "bold"))

    def build_connection_frame(self, parent):
        frame = ttk.LabelFrame(parent, text="Connection", style="Card.TLabelframe")
        frame.pack(fill="x")

        ttk.Label(frame, text="COM Port:").pack(side="left", padx=(0, 4))

        self.port_combo = ttk.Combobox(frame, textvariable=self.port_var, width=16, state="readonly")
        self.port_combo.pack(side="left", padx=4)

        ttk.Button(frame, text="Refresh", command=self.refresh_ports, style="Command.TButton").pack(side="left", padx=4)
        ttk.Button(frame, text="Connect", command=self.connect, style="Accent.TButton").pack(side="left", padx=4)
        ttk.Button(frame, text="Disconnect", command=self.disconnect, style="Command.TButton").pack(side="left", padx=4)

        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=10)

        self.manual_entry = ttk.Entry(frame)
        self.manual_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.manual_entry.bind("<Return>", lambda event: self.send_manual_command())

        ttk.Button(frame, text="Send manual command", command=self.send_manual_command, style="Command.TButton").pack(side="left", padx=4)

    def build_command_notebook(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=False)

        self.build_general_tab(notebook)
        self.build_led_tab(notebook)
        self.build_i2c_tab(notebook)
        self.build_pwm_tab(notebook)

    def build_general_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="General")

        commands = [
            ("Help", "help"),
            ("Read ADC / LM235", "readADC"),
            ("Stream ADC ON", "streamADC_on"),
            ("Stream ADC OFF", "streamADC_off"),
            ("Read TMP126", "readSPI_TMP"),
            ("Read TMP ID", "readTMP_ID"),
        ]

        self.add_button_grid(tab, commands, columns=2)

    def build_led_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="LED")

        commands = [
            ("Red ON", "redLED_on"),
            ("Red OFF", "redLED_off"),
            ("Green ON", "greenLED_on"),
            ("Green OFF", "greenLED_off"),
            ("Yellow ON", "yellowLED_on"),
            ("Yellow OFF", "yellowLED_off"),
            ("Toggle all LEDs", "toggleLEDs"),
        ]

        self.add_button_grid(tab, commands, columns=2)

    def build_i2c_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="GPIO Expander")

        ttk.Button(tab, text="Scan I2C", command=lambda: self.send_command("scanI2C"), style="Command.TButton").grid(
            row=0, column=0, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(tab, text="Get GPIO", command=lambda: self.send_command("getGPIO"), style="Command.TButton").grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )

        ttk.Label(tab, text="P0 HEX:").grid(row=1, column=0, padx=5, pady=(14, 5), sticky="w")
        ttk.Entry(tab, textvariable=self.p0_var, width=8).grid(row=1, column=1, padx=5, pady=(14, 5), sticky="ew")

        ttk.Label(tab, text="P1 HEX:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(tab, textvariable=self.p1_var, width=8).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(tab, text="Set GPIO P0/P1", command=self.send_set_gpio, style="Accent.TButton").grid(
            row=3, column=0, columnspan=2, padx=5, pady=8, sticky="ew"
        )

        legacy = [
            ("Read I2C", "readI2C"),
            ("I2C HIGH", "writeI2C_high"),
            ("I2C LOW", "writeI2C_low"),
            ("I2C Toggle", "toggleI2C"),
        ]
        for index, (label, command) in enumerate(legacy):
            ttk.Button(tab, text=label, command=lambda cmd=command: self.send_command(cmd), style="Command.TButton").grid(
                row=4 + index // 2, column=index % 2, padx=5, pady=5, sticky="ew"
            )

        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)

    def build_pwm_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="PWM")

        ttk.Label(tab, text="Duty cycle [%]:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(tab, textvariable=self.pwm_var, width=8).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(tab, text="Set PWM", command=self.send_set_pwm, style="Accent.TButton").grid(
            row=0, column=2, padx=5, pady=5, sticky="ew"
        )

        quick_values = [0, 10, 25, 50, 75, 90, 100]
        for index, value in enumerate(quick_values):
            ttk.Button(
                tab,
                text=f"{value}%",
                command=lambda duty=value: self.send_pwm_value(duty),
                style="Command.TButton"
            ).grid(row=1 + index // 4, column=index % 4, padx=5, pady=5, sticky="ew")

        ttk.Button(tab, text="Sine ON", command=lambda: self.send_command("pwmSine_on"), style="Accent.TButton").grid(
            row=3, column=0, padx=5, pady=(12, 5), sticky="ew"
        )
        ttk.Button(tab, text="Sine OFF", command=lambda: self.send_command("pwmSine_off"), style="Command.TButton").grid(
            row=3, column=1, padx=5, pady=(12, 5), sticky="ew"
        )

        info = ttk.Label(
            tab,
            text="PB3/PWM_OUT: square PWM signal\nJ6/OpAmp: filtered sine when pwmSine_on is active",
            justify="left"
        )
        info.grid(row=4, column=0, columnspan=4, padx=5, pady=(10, 0), sticky="w")

        for col in range(4):
            tab.columnconfigure(col, weight=1)

    def add_button_grid(self, parent, commands, columns=2):
        for index, (label, command) in enumerate(commands):
            ttk.Button(
                parent,
                text=label,
                command=lambda cmd=command: self.send_command(cmd),
                style="Command.TButton"
            ).grid(row=index // columns, column=index % columns, padx=5, pady=5, sticky="ew")

        for col in range(columns):
            parent.columnconfigure(col, weight=1)

    def build_measurement_cards(self, parent):
        frame = ttk.LabelFrame(parent, text="Last measurements", style="Card.TLabelframe")
        frame.pack(fill="x", pady=(10, 0))

        cards = [
            ("LM235 analog", self.last_lm235_var),
            ("TMP126 digital", self.last_tmp126_var),
            ("ADC raw", self.last_adc_var),
            ("ADC voltage", self.last_voltage_var),
            ("GPIO Expander", self.last_gpio_var),
            ("PWM duty", self.last_pwm_var),
        ]

        for index, (label, variable) in enumerate(cards):
            row = index // 2
            col = index % 2

            card = ttk.Frame(frame, padding=8)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="ew")

            ttk.Label(card, text=label).pack(anchor="w")
            ttk.Label(card, textvariable=variable, style="Value.TLabel").pack(anchor="w")

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def build_graphs(self, parent):
        graph_frame = ttk.LabelFrame(parent, text="Live temperature graphs", style="Card.TLabelframe")
        graph_frame.pack(fill="both", expand=True)

        self.figure = Figure(figsize=(7.2, 4.2), dpi=100)
        self.ax_temp = self.figure.add_subplot(111)
        self.ax_temp.set_title("Analog and digital temperature")
        self.ax_temp.set_xlabel("Sample")
        self.ax_temp.set_ylabel("Temperature [°C]")
        self.ax_temp.grid(True, alpha=0.3)

        self.lm235_line, = self.ax_temp.plot([], [], marker="o", linewidth=1.5, markersize=3, label="LM235 analog")
        self.tmp126_line, = self.ax_temp.plot([], [], marker="s", linewidth=1.5, markersize=3, label="TMP126 digital")
        self.ax_temp.legend(loc="best")

        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        graph_buttons = ttk.Frame(graph_frame)
        graph_buttons.pack(fill="x", pady=(6, 0))

        ttk.Button(graph_buttons, text="Clear graphs", command=self.clear_graphs, style="Command.TButton").pack(side="left")
        ttk.Button(graph_buttons, text="Read both sensors", command=self.read_both_sensors, style="Accent.TButton").pack(side="left", padx=6)

    def build_output(self, parent):
        output_frame = ttk.LabelFrame(parent, text="Terminal output", style="Card.TLabelframe")
        output_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.output_text = scrolledtext.ScrolledText(output_frame, height=12, font=("Consolas", 10))
        self.output_text.pack(fill="both", expand=True)

    # -------------------------------------------------------------------------
    # Serial connection
    # -------------------------------------------------------------------------
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
                "p0_hex",
                "p1_hex",
                "int_pin",
                "pwm_duty_percent",
                "line"
            ])

            self.reader_running = True

            reader_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
            reader_thread.start()

            self.connection_var.set(f"Connected to {port}")
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

        self.connection_var.set("Disconnected")
        self.log("Disconnected.\n")

    # -------------------------------------------------------------------------
    # Command helpers
    # -------------------------------------------------------------------------
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

    def send_set_gpio(self):
        p0 = self.normalize_hex_byte(self.p0_var.get())
        p1 = self.normalize_hex_byte(self.p1_var.get())

        if p0 is None or p1 is None:
            messagebox.showerror("Invalid HEX", "Use two HEX characters for P0 and P1, for example B2 and C4.")
            return

        self.p0_var.set(p0)
        self.p1_var.set(p1)
        self.send_command(f"setGPIO.{p0}.{p1}")

    def send_set_pwm(self):
        try:
            duty = int(self.pwm_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid duty", "Use an integer from 0 to 100.")
            return

        self.send_pwm_value(duty)

    def send_pwm_value(self, duty):
        if duty < 0 or duty > 100:
            messagebox.showerror("Invalid duty", "Use an integer from 0 to 100.")
            return

        self.pwm_var.set(str(duty))
        self.send_command(f"setPWM.{duty}")

    def read_both_sensors(self):
        self.send_command("readADC")
        self.root.after(250, lambda: self.send_command("readSPI_TMP"))

    @staticmethod
    def normalize_hex_byte(text):
        clean = text.strip().upper().replace("0X", "")

        if len(clean) == 1:
            clean = "0" + clean

        if len(clean) != 2:
            return None

        if not re.fullmatch(r"[0-9A-F]{2}", clean):
            return None

        return clean

    # -------------------------------------------------------------------------
    # Serial receiver and parsing
    # -------------------------------------------------------------------------
    def read_serial_loop(self):
        while self.reader_running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    line = self.serial_port.readline()

                    if line:
                        text = line.decode("ascii", errors="replace")
                        self.root.after(0, self.handle_received_line, text)

            except serial.SerialException as error:
                self.root.after(0, self.log, f"Serial read error: {error}\n")
                self.reader_running = False

    def handle_received_line(self, text):
        self.save_measurement_to_csv(text)
        self.update_live_values(text)
        self.log(text)

    def save_measurement_to_csv(self, line):
        if not self.csv_writer:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        data = self.parse_line(line)

        self.csv_writer.writerow([
            timestamp,
            data["source"],
            data["raw"],
            data["voltage_mv"],
            data["temperature_c"],
            data["value_hex"],
            data["p0_hex"],
            data["p1_hex"],
            data["int_pin"],
            data["pwm_duty_percent"],
            data["line"]
        ])

        self.csv_file.flush()

    def update_live_values(self, line):
        data = self.parse_line(line)

        if data["source"] == "LM235_ADC":
            self.last_adc_var.set(data["raw"])
            self.last_voltage_var.set(f"{data['voltage_mv']} mV")
            self.last_lm235_var.set(f"{data['temperature_c']} °C")
            self.add_temperature_point("LM235", float(data["temperature_c"]))

        elif data["source"] == "TMP126":
            self.last_tmp126_var.set(f"{data['temperature_c']} °C")
            self.add_temperature_point("TMP126", float(data["temperature_c"]))

        elif data["source"] == "PCF8575":
            self.last_gpio_var.set(
                f"{data['value_hex']}  P0={data['p0_hex']}  P1={data['p1_hex']}  INT={data['int_pin']}"
            )

        elif data["source"] == "PWM":
            self.last_pwm_var.set(f"{data['pwm_duty_percent']} %")

    def parse_line(self, line):
        clean_line = line.strip()

        data = {
            "source": "UART",
            "raw": "",
            "voltage_mv": "",
            "temperature_c": "",
            "value_hex": "",
            "p0_hex": "",
            "p1_hex": "",
            "int_pin": "",
            "pwm_duty_percent": "",
            "line": clean_line,
        }

        tmp_match = re.search(
            r"TMP126 raw=0x([0-9A-Fa-f]+), temp=([+-]?\d+\.\d+) C",
            clean_line
        )

        adc_match = re.search(
            r"ADC raw=(\d+), voltage=(\d+) mV, LM235=([+-]?\d+\.\d+) C",
            clean_line
        )

        gpio_match = re.search(
            r"PCF8575 (?:input|output) = 0x([0-9A-Fa-f]+)(?:, P0=0x([0-9A-Fa-f]{2}), P1=0x([0-9A-Fa-f]{2}))?(?:, INT=(\d+))?",
            clean_line
        )

        old_i2c_match = re.search(
            r"PCF8575 input = 0x([0-9A-Fa-f]+), INT=(\d+)",
            clean_line
        )

        pwm_match = re.search(
            r"PWM duty = (\d+)%",
            clean_line
        )

        if tmp_match:
            data["source"] = "TMP126"
            data["raw"] = "0x" + tmp_match.group(1)
            data["temperature_c"] = tmp_match.group(2)

        elif adc_match:
            data["source"] = "LM235_ADC"
            data["raw"] = adc_match.group(1)
            data["voltage_mv"] = adc_match.group(2)
            data["temperature_c"] = adc_match.group(3)

        elif gpio_match:
            data["source"] = "PCF8575"
            data["value_hex"] = "0x" + gpio_match.group(1).upper()
            data["p0_hex"] = "0x" + gpio_match.group(2).upper() if gpio_match.group(2) else ""
            data["p1_hex"] = "0x" + gpio_match.group(3).upper() if gpio_match.group(3) else ""
            data["int_pin"] = gpio_match.group(4) if gpio_match.group(4) else ""

        elif old_i2c_match:
            data["source"] = "PCF8575"
            data["value_hex"] = "0x" + old_i2c_match.group(1).upper()
            data["int_pin"] = old_i2c_match.group(2)

        elif pwm_match:
            data["source"] = "PWM"
            data["pwm_duty_percent"] = pwm_match.group(1)

        return data

    def add_temperature_point(self, source, temperature):
        self.sample_index += 1

        if source == "LM235":
            self.lm235_times.append(self.sample_index)
            self.lm235_temps.append(temperature)
        elif source == "TMP126":
            self.tmp126_times.append(self.sample_index)
            self.tmp126_temps.append(temperature)

        self.update_graph()

    def update_graph(self):
        self.lm235_line.set_data(list(self.lm235_times), list(self.lm235_temps))
        self.tmp126_line.set_data(list(self.tmp126_times), list(self.tmp126_temps))

        all_x = list(self.lm235_times) + list(self.tmp126_times)
        all_y = list(self.lm235_temps) + list(self.tmp126_temps)

        if all_x and all_y:
            self.ax_temp.set_xlim(max(0, min(all_x) - 1), max(all_x) + 1)

            y_min = min(all_y)
            y_max = max(all_y)
            margin = max(1.0, (y_max - y_min) * 0.15)
            self.ax_temp.set_ylim(y_min - margin, y_max + margin)

        self.canvas.draw_idle()

    def clear_graphs(self):
        self.lm235_times.clear()
        self.lm235_temps.clear()
        self.tmp126_times.clear()
        self.tmp126_temps.clear()
        self.sample_index = 0
        self.update_graph()

    # -------------------------------------------------------------------------
    # Output log
    # -------------------------------------------------------------------------
    def log(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def on_close(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = STM32ControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
