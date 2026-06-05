# STM32 PC Control App

Applicazione Python per comandare la scheda STM32 tramite porta seriale.

La stessa applicazione può essere usata sia con USART tramite adattatore seriale, sia con USB CDC, perché entrambi vengono visti dal PC come porte COM.

## Installazione

Aprire Git Bash o PowerShell nella cartella `Python` e installare le dipendenze:

```bash
py -m pip install -r requirements.txt
```

## Avvio

```bash
py pc_control_app.py
```

## Funzioni principali

- Connessione alla porta COM.
- Invio comandi manuali.
- Pulsanti rapidi per LED, ADC, TMP126, I2C/GPIO Expander e PWM.
- Comandi GPIO Expander:
  - `getGPIO`
  - `setGPIO.P0.P1`, per esempio `setGPIO.B2.C4`
- Comandi PWM:
  - `setPWM.x`, con `x` da 0 a 100
  - `pwmSine_on`
  - `pwmSine_off`
- Grafico live delle temperature:
  - LM235 analogico letto tramite ADC
  - TMP126 digitale letto tramite SPI
- Salvataggio automatico log CSV.

## Note sui grafici

Il grafico si aggiorna quando il firmware restituisce righe nel formato:

```text
ADC raw=..., voltage=... mV, LM235=... C
TMP126 raw=0x...., temp=... C
```

Per leggere entrambi i sensori è disponibile il pulsante **Read both sensors**.

## Creazione eseguibile Windows

Per generare il file `.exe`, usare:

```text
build_exe.bat
```

Il file finale viene creato in:

```text
dist/STM32_PC_Control.exe
```

Se l'eseguibile non parte, usare:

```text
build_exe_debug.bat
```

La versione debug apre anche una console per mostrare eventuali errori.
