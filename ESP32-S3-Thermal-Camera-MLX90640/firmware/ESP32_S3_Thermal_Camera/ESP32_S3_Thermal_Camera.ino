#include <Wire.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <Adafruit_MLX90640.h>

// =============================================================
// InnoCircuitsLab — ESP32-S3 Thermal Camera
// ESP32-S3 Super Mini + MLX90640 + ST7789 240x320 TFT
// =============================================================

// ----- MLX90640 (I2C) -----
static const uint8_t I2C_SDA = 8;
static const uint8_t I2C_SCL = 9;
static const uint8_t MLX_ADDR = 0x33;

// ----- ST7789 (SPI) -----
static const uint8_t TFT_CS   = 10;
static const uint8_t TFT_DC   = 5;
static const uint8_t TFT_RST  = 6;
static const uint8_t TFT_MOSI = 11;
static const uint8_t TFT_SCLK = 12;

// ----- Thermal display settings -----
static const float DISPLAY_MIN_C = 20.0f;
static const float DISPLAY_MAX_C = 40.0f;

// Sensor is physically 32x24 = 768 measurements.
static const int SENSOR_W = 32;
static const int SENSOR_H = 24;

// We interpolate once to 64x48 for a smoother display.
// This improves readability only; it does NOT add measured detail.
static const int INTERP_W = 64;
static const int INTERP_H = 48;

// Final on-screen thermal image dimensions used in this project.
static const int IMG_X = 12;
static const int IMG_Y = 48;
static const int IMG_W = 184;
static const int IMG_H = 138;

Adafruit_MLX90640 mlx;
Adafruit_ST7789 tft(TFT_CS, TFT_DC, TFT_RST);

float thermalFrame[SENSOR_W * SENSOR_H];
float interpolated[INTERP_W * INTERP_H];

float frameMin = 0.0f;
float frameMax = 0.0f;
float centerTemp = 0.0f;
int hottestX = 0;
int hottestY = 0;

// -------------------------------------------------------------
// RGB565 helper
// -------------------------------------------------------------
uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

uint8_t lerp8(uint8_t a, uint8_t b, float t) {
  return (uint8_t)(a + (b - a) * t);
}

// Approximate ironbow-style palette.
uint16_t ironbow(float normalized) {
  if (normalized < 0.0f) normalized = 0.0f;
  if (normalized > 1.0f) normalized = 1.0f;

  struct Stop { float p; uint8_t r, g, b; };
  static const Stop stops[] = {
    {0.00f,   6,   8,  24},
    {0.18f,  25,  12,  88},
    {0.38f, 108,  18, 120},
    {0.58f, 214,  45,  68},
    {0.78f, 252, 126,  32},
    {0.92f, 255, 220,  72},
    {1.00f, 255, 250, 226}
  };

  const int count = sizeof(stops) / sizeof(stops[0]);
  for (int i = 0; i < count - 1; i++) {
    if (normalized >= stops[i].p && normalized <= stops[i + 1].p) {
      float t = (normalized - stops[i].p) / (stops[i + 1].p - stops[i].p);
      return rgb565(
        lerp8(stops[i].r, stops[i + 1].r, t),
        lerp8(stops[i].g, stops[i + 1].g, t),
        lerp8(stops[i].b, stops[i + 1].b, t)
      );
    }
  }

  return rgb565(255, 250, 226);
}

uint16_t temperatureToColor(float tempC) {
  float n = (tempC - DISPLAY_MIN_C) / (DISPLAY_MAX_C - DISPLAY_MIN_C);
  return ironbow(n);
}

// -------------------------------------------------------------
// 32x24 -> 64x48 bilinear interpolation
// -------------------------------------------------------------
void interpolateFrame() {
  for (int y = 0; y < INTERP_H; y++) {
    float srcY = ((float)y * (SENSOR_H - 1)) / (INTERP_H - 1);
    int y0 = (int)srcY;
    int y1 = min(y0 + 1, SENSOR_H - 1);
    float fy = srcY - y0;

    for (int x = 0; x < INTERP_W; x++) {
      float srcX = ((float)x * (SENSOR_W - 1)) / (INTERP_W - 1);
      int x0 = (int)srcX;
      int x1 = min(x0 + 1, SENSOR_W - 1);
      float fx = srcX - x0;

      float p00 = thermalFrame[y0 * SENSOR_W + x0];
      float p10 = thermalFrame[y0 * SENSOR_W + x1];
      float p01 = thermalFrame[y1 * SENSOR_W + x0];
      float p11 = thermalFrame[y1 * SENSOR_W + x1];

      float top = p00 + (p10 - p00) * fx;
      float bottom = p01 + (p11 - p01) * fx;
      interpolated[y * INTERP_W + x] = top + (bottom - top) * fy;
    }
  }
}

// -------------------------------------------------------------
// Find min, max, hottest location and center temperature
// -------------------------------------------------------------
void analyzeFrame() {
  frameMin = thermalFrame[0];
  frameMax = thermalFrame[0];
  int maxIndex = 0;

  for (int i = 1; i < SENSOR_W * SENSOR_H; i++) {
    float t = thermalFrame[i];
    if (t < frameMin) frameMin = t;
    if (t > frameMax) {
      frameMax = t;
      maxIndex = i;
    }
  }

  hottestX = maxIndex % SENSOR_W;
  hottestY = maxIndex / SENSOR_W;

  // Average the four central sensor measurements.
  float c1 = thermalFrame[11 * SENSOR_W + 15];
  float c2 = thermalFrame[11 * SENSOR_W + 16];
  float c3 = thermalFrame[12 * SENSOR_W + 15];
  float c4 = thermalFrame[12 * SENSOR_W + 16];
  centerTemp = (c1 + c2 + c3 + c4) * 0.25f;
}

// -------------------------------------------------------------
// Static UI
// -------------------------------------------------------------
void drawStaticUI() {
  tft.fillScreen(ST77XX_BLACK);

  tft.setTextWrap(false);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(12, 10);
  tft.print("THERMAL CAMERA");

  tft.setTextSize(1);
  tft.setTextColor(rgb565(130, 150, 170));
  tft.setCursor(12, 31);
  tft.print("MLX90640 32x24  |  ESP32-S3");

  // Heat-map border
  tft.drawRoundRect(IMG_X - 2, IMG_Y - 2, IMG_W + 4, IMG_H + 4, 4, rgb565(75, 90, 108));

  // Right-side information panel
  tft.drawRoundRect(210, 48, 100, 138, 5, rgb565(55, 68, 84));

  tft.setTextColor(rgb565(150, 165, 182));
  tft.setTextSize(1);
  tft.setCursor(222, 61);  tft.print("MIN");
  tft.setCursor(222, 101); tft.print("MAX");
  tft.setCursor(222, 141); tft.print("CENTER");

  tft.setCursor(12, 204);
  tft.setTextColor(rgb565(150, 165, 182));
  tft.print("DISPLAY RANGE");

  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(12, 220);
  tft.print(DISPLAY_MIN_C, 0);
  tft.print("C");

  tft.setCursor(164, 220);
  tft.print(DISPLAY_MAX_C, 0);
  tft.print("C");

  // Palette bar
  for (int x = 45; x < 158; x++) {
    float n = (float)(x - 45) / (158 - 45 - 1);
    uint16_t c = ironbow(n);
    tft.drawFastVLine(x, 216, 12, c);
  }
}

// -------------------------------------------------------------
// Draw thermal image and overlays
// -------------------------------------------------------------
void drawThermalImage() {
  // Map the 64x48 interpolated image into the 184x138 display rectangle.
  // No temporal smoothing is used.
  for (int py = 0; py < IMG_H; py++) {
    int sy = (py * INTERP_H) / IMG_H;
    if (sy >= INTERP_H) sy = INTERP_H - 1;

    for (int px = 0; px < IMG_W; px++) {
      int sx = (px * INTERP_W) / IMG_W;
      if (sx >= INTERP_W) sx = INTERP_W - 1;

      float temp = interpolated[sy * INTERP_W + sx];
      tft.drawPixel(IMG_X + px, IMG_Y + py, temperatureToColor(temp));
    }
  }

  // Center crosshair
  int cx = IMG_X + IMG_W / 2;
  int cy = IMG_Y + IMG_H / 2;
  uint16_t cross = ST77XX_WHITE;
  tft.drawFastHLine(cx - 7, cy, 15, cross);
  tft.drawFastVLine(cx, cy - 7, 15, cross);

  // Hottest point marker derived from the original 32x24 frame.
  int hx = IMG_X + (hottestX * IMG_W) / SENSOR_W;
  int hy = IMG_Y + (hottestY * IMG_H) / SENSOR_H;
  tft.drawCircle(hx, hy, 4, rgb565(255, 255, 255));
}

void drawMeasurements() {
  // Clear only the changing value areas.
  tft.fillRect(218, 73, 84, 22, ST77XX_BLACK);
  tft.fillRect(218, 113, 84, 22, ST77XX_BLACK);
  tft.fillRect(218, 153, 84, 22, ST77XX_BLACK);

  tft.setTextSize(2);

  tft.setTextColor(rgb565(100, 214, 255));
  tft.setCursor(220, 75);
  tft.print(frameMin, 1);
  tft.print("C");

  tft.setTextColor(rgb565(255, 133, 82));
  tft.setCursor(220, 115);
  tft.print(frameMax, 1);
  tft.print("C");

  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(220, 155);
  tft.print(centerTemp, 1);
  tft.print("C");
}

// -------------------------------------------------------------
// Setup
// -------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(300);

  // Separate buses: MLX90640 on I2C, TFT on SPI.
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(1000000);  // If unstable on your wiring, try 400000.

  SPI.begin(TFT_SCLK, -1, TFT_MOSI, TFT_CS);

  tft.init(240, 320);
  tft.setRotation(1);  // 320x240 landscape
  tft.setSPISpeed(40000000);

  drawStaticUI();

  if (!mlx.begin(MLX_ADDR, &Wire)) {
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextColor(ST77XX_RED);
    tft.setTextSize(2);
    tft.setCursor(20, 100);
    tft.println("MLX90640 ERROR");
    tft.setTextSize(1);
    tft.setCursor(20, 130);
    tft.println("Check SDA/SCL and 3.3V pull-ups");
    while (true) delay(100);
  }

  mlx.setMode(MLX90640_CHESS);
  mlx.setResolution(MLX90640_ADC_18BIT);
  mlx.setRefreshRate(MLX90640_8_HZ);

  delay(500);
}

// -------------------------------------------------------------
// Main loop
// -------------------------------------------------------------
void loop() {
  if (mlx.getFrame(thermalFrame) != 0) {
    Serial.println("MLX90640 frame read failed");
    return;
  }

  analyzeFrame();
  interpolateFrame();
  drawThermalImage();
  drawMeasurements();

  Serial.print("MIN: ");
  Serial.print(frameMin, 1);
  Serial.print(" C  MAX: ");
  Serial.print(frameMax, 1);
  Serial.print(" C  CENTER: ");
  Serial.print(centerTemp, 1);
  Serial.println(" C");
}
