clear;
clc;
close all;

[file, path] = uigetfile("*.csv", "Select STM32 UART log file");

if isequal(file, 0)
    disp("No file selected.");
    return;
end

filename = fullfile(path, file);

data = readtable(filename, "TextType", "string");

data.timestamp = datetime(string(data.timestamp), ...
    "InputFormat", "yyyy-MM-dd HH:mm:ss.SSS");

data.source = string(data.source);

tmp126_data = data(data.source == "TMP126", :);
lm235_data = data(data.source == "LM235_ADC", :);
pcf8575_data = data(data.source == "PCF8575", :);

% Create output folder for figures inside the Matlab folder
[~, csv_name, ~] = fileparts(file);

script_folder = fileparts(mfilename("fullpath"));
figures_folder = fullfile(script_folder, "figures_" + string(csv_name));

if ~exist(figures_folder, "dir")
    mkdir(figures_folder);
end

disp("Figures will be saved in:");
disp(figures_folder);

% TMP126 digital temperature plot
if ~isempty(tmp126_data)
    tmp126_temp = column_to_double(tmp126_data.temperature_c);

    figure;
    plot(tmp126_data.timestamp, tmp126_temp, "-o", "LineWidth", 1.2);
    grid on;
    xlabel("Time");
    ylabel("Temperature [°C]");
    title("TMP126 Digital Temperature");

    save_current_figure(figures_folder, "tmp126_digital_temperature.png");
end

% LM235 analog temperature, ADC voltage and ADC raw plots
if ~isempty(lm235_data)
    lm235_temp = column_to_double(lm235_data.temperature_c);
    adc_voltage = column_to_double(lm235_data.voltage_mv);

    % ADC raw reconstructed from voltage using measured VDDA = 3439 mV
    adc_raw = round(adc_voltage * 4095 / 3439);

    figure;
    plot(lm235_data.timestamp, lm235_temp, "-o", "LineWidth", 1.2);
    grid on;
    xlabel("Time");
    ylabel("Temperature [°C]");
    title("LM235 Analog Temperature");

    save_current_figure(figures_folder, "lm235_analog_temperature.png");

    figure;
    plot(lm235_data.timestamp, adc_voltage, "-o", "LineWidth", 1.2);
    grid on;
    xlabel("Time");
    ylabel("Voltage [mV]");
    title("ADC Voltage");

    save_current_figure(figures_folder, "adc_voltage.png");

    figure;
    plot(lm235_data.timestamp, adc_raw, "-o", "LineWidth", 1.2);
    grid on;
    xlabel("Time");
    ylabel("ADC Raw Value");
    title("ADC Raw Values");

    save_current_figure(figures_folder, "adc_raw_values.png");
end

% Temperature comparison plot
if ~isempty(tmp126_data) && ~isempty(lm235_data)
    figure;
    hold on;

    plot(tmp126_data.timestamp, ...
         column_to_double(tmp126_data.temperature_c), ...
         "-o", "LineWidth", 1.2);

    plot(lm235_data.timestamp, ...
         column_to_double(lm235_data.temperature_c), ...
         "-o", "LineWidth", 1.2);

    grid on;
    xlabel("Time");
    ylabel("Temperature [°C]");
    title("Temperature Comparison");
    legend("TMP126", "LM235");
    hold off;

    save_current_figure(figures_folder, "temperature_comparison.png");
end

% PCF8575 readings table
if ~isempty(pcf8575_data)
    disp("PCF8575 readings:");
    disp(pcf8575_data(:, ["timestamp", "value_hex", "int_pin"]));
end

disp("Figure export completed.");

function y = column_to_double(x)
    if isnumeric(x)
        y = double(x);
    else
        y = str2double(erase(string(x), "+"));
    end
end

function save_current_figure(folder, filename)
    output_file = fullfile(folder, filename);

    set(gcf, "Color", "w");

    print(gcf, output_file, "-dpng", "-r600");

    disp("Saved figure:");
    disp(output_file);
end