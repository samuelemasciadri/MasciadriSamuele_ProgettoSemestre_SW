# Creazione file `.exe`

Per creare l'eseguibile Windows del software PC:

1. Aprire la cartella:

   ```text
   A4- SW/Python
   ```

2. Fare doppio click su:

   ```text
   build_exe.bat
   ```

3. Al termine della compilazione, l'eseguibile viene creato in:

   ```text
   A4- SW/Python/dist/STM32_PC_Control.exe
   ```

## Avvio dell'applicazione

Dopo la creazione dell'eseguibile, è possibile avviare il software direttamente con doppio click su:

```text
dist/STM32_PC_Control.exe
```

Non è più necessario avviare il programma con:

```text
py pc_control_app.py
```

## Se qualcosa non funziona

Se l'eseguibile non parte o si chiude subito, usare la versione debug:

```text
build_exe_debug.bat
```

Questa crea:

```text
dist/STM32_PC_Control_Debug.exe
```

La versione debug mantiene aperta anche una finestra console, utile per leggere eventuali errori.

## Note

La prima compilazione può richiedere alcuni minuti perché PyInstaller deve analizzare e includere le librerie usate dal programma, tra cui `pyserial`, `tkinter` e `matplotlib`.

Le cartelle `build/`, `dist/` e il file `.spec` sono generati automaticamente e non devono essere modificati a mano.
