# Thermal-imaging notes

## The sensor is really 32 × 24

The MLX90640 produces **32 × 24 = 768 measured temperature points** per frame.

The firmware interpolates that data to a larger image so the result is easier to read on the TFT. Interpolation makes the display smoother, but it does **not** create thermal detail that the sensor never measured.

## Why distance matters

A small component occupies fewer thermal samples as the camera moves farther away. Two nearby components can also blend into a single larger hotspot. For electronics inspection, the camera works best at relatively close range.

## Fixed palette range

The included firmware maps the display over a fixed **20–40 °C** range. This makes visual comparisons consistent from frame to frame. Change `DISPLAY_MIN_C` and `DISPLAY_MAX_C` in the sketch if your application needs a different range.

## Emissivity and shiny surfaces

Thermal cameras measure infrared radiation, not temperature directly. Different surfaces emit and reflect infrared energy differently. Shiny metal can therefore appear misleading compared with a matte surface at a similar physical temperature.

This project is best treated as a **relative hotspot finder**, not a calibrated precision thermometer.

## Safe electronics testing

Use low-voltage electronics for experiments. A hotspot can tell you where to investigate, but it does not by itself prove that a component is faulty.
