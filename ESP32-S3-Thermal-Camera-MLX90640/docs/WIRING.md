# Wiring

This repository documents the wiring used for the ESP32-S3 thermal-camera build.

## MLX90640 → ESP32-S3 Super Mini

| MLX90640 | ESP32-S3 | Notes |
|---|---|---|
| VCC / VIN | 3.3V | Use 3.3 V for this build |
| GND | GND | Common ground |
| SDA | GPIO 8 | I2C data |
| SCL | GPIO 9 | I2C clock |

### I2C pull-ups

The physical build used external pull-up resistors of approximately **2 kΩ**:

- SDA → 3.3 V through ~2 kΩ
- SCL → 3.3 V through ~2 kΩ

The MLX90640 default I2C address is **0x33**.

## ST7789 TFT → ESP32-S3 Super Mini

| ST7789 | ESP32-S3 | Notes |
|---|---|---|
| VCC | 3.3V | Display logic/power used at 3.3 V in this build |
| GND | GND | Common ground |
| SCK / CLK | GPIO 12 | SPI clock |
| MOSI / SDA | GPIO 11 | SPI data to display |
| CS | GPIO 10 | Chip select |
| DC | GPIO 5 | Data/command |
| RST / RES | GPIO 6 | Display reset |
| BL / LED | 3.3V | If your module exposes a backlight pin |
| MISO | Not connected | Not required for this project |

## Bus layout

```text
MLX90640 (I2C)                    ST7789 (SPI)

3.3V ───────────── VCC            3.3V ───────── VCC
GND  ───────────── GND            GND  ───────── GND
GPIO8 ──────────── SDA            GPIO12 ─────── SCK
GPIO9 ──────────── SCL            GPIO11 ─────── MOSI
  │                                  GPIO10 ─────── CS
  ├─ ~2kΩ ── 3.3V                    GPIO5  ─────── DC
  └─ ~2kΩ ── 3.3V                    GPIO6  ─────── RST
```

## Important

ESP32-S3 board layouts vary. The GPIO numbers above are the **logical GPIO numbers**, not a claim about identical physical pin positions on every ESP32-S3 board.
