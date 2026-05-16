# STM32 PC Control Software

Simple Python GUI used to control the STM32 firmware through UART serial communication.

## Features

- Select and connect to a COM port
- Send UART commands to the STM32 board
- Read TMP126 digital temperature sensor
- Read analog temperature sensor through ADC
- Start and stop ADC streaming
- Test PCF8575 I2C GPIO expander
- Control debug LEDs

## Requirements

- Python 3
- pyserial

Install dependencies with:

```bash
pip install -r requirements.txt