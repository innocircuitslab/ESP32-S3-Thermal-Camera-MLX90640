# Tests used in the project

These are the practical tests used to understand where the 32×24 sensor is useful and where it is limited.

## 1. Hand / warm object

Point the sensor at a hand, warm cup or similar object at close range. Large warm objects should be easy to separate from the cooler background.

## 2. Distance / resolution

Use the same target at several distances. At close range the hotspot occupies more measured points. At longer distance the same target becomes less spatially distinct.

## 3. Electronics hotspot

Scan a safe low-voltage PCB after it has been powered long enough to reach a stable operating temperature. Look for regions that stand out relative to the surrounding board.

A hotter region is a **starting point for troubleshooting**, not automatic proof of a fault.

## 4. Raw vs interpolated display

Compare a raw 32×24 visualization with the smoothed display. The interpolated version should be easier to interpret while still representing the same 768 measured samples.
