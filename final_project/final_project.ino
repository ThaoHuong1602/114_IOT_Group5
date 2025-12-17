#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <cJSON.h>
#include <Wire.h>
#include <Adafruit_NeoPixel.h>
#include "DFRobot_INA219.h"

// ------------ Device ID ------------
uint8_t deviceID = 0;
String cmd = "";
uint8_t val = 0;
uint8_t operationMode = 0; // operation mode

// ------------ LoRa Module ------------
#define LORA_SS         2
#define LORA_RST        15
#define LORA_DIO0       16
#define LORA_FREQ       923E6     // adjust for your region
#define MAX_PACKET_LEN  256       // Length of received data buffer
char rxBuffer[MAX_PACKET_LEN];    // Buffer for received data

// ------------ RGB Led ------------
// #define LED_GREEN 25
// #define LED_BLUE  26
// #define LED_RED   27
// #define LED_COMMON_ANODE  33
uint8_t ledBrightness = 255;
uint8_t ledColor = 2;
#define PIN         17
#define NUMPIXELS   8
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

// ------------ Power Meter ------------
DFRobot_INA219_IIC ina219(&Wire, INA219_I2C_ADDRESS4);
float ina219Reading_mA = 1000;
float extMeterReading_mA = 1000;

uint8_t voltage = 0;
uint8_t current = 0;
uint8_t power = 0;

// ------------ Light Sensor ------------
#define LIGHT_SENSOR_PIN  35
uint8_t ambientLightIntensity = 0;

// ------------ Motion Sensor ------------
#define MOTION_SENSOR_PIN  32
bool isMotion = false;

// ------------ Rain Sensor ------------
#define RAIN_SENSOR_PIN   34
bool isRain = false;

// ------------ FreeRTOS ------------
TaskHandle_t loraRxTaskHandle   = NULL;
TaskHandle_t loraTxTaskHandle   = NULL;
TaskHandle_t heartbeatTaskHandle = NULL;

SemaphoreHandle_t loraMutex;   // to protect LoRa access

// ------------ LoRa RX Task ------------
void LoRaRxTask(void *pvParameters) {
  (void) pvParameters;

  for (;;) {
    // Take mutex before accessing LoRa
    if (xSemaphoreTake(loraMutex, portMAX_DELAY) == pdTRUE) {
      int packetSize = LoRa.parsePacket();  // non-blocking

      if (packetSize) {
        int index = 0;
        memset(rxBuffer, 0, MAX_PACKET_LEN);

        Serial.print("[RX] Packet: ");

        while (LoRa.available() && index < (MAX_PACKET_LEN - 1)) {
          char c = (char)LoRa.read();
          rxBuffer[index++] = c;
          Serial.print(c);
        }
        rxBuffer[index] = '\0';

        Serial.print(" | RSSI: ");
        Serial.println(LoRa.packetRssi());

        parseJsonMessage(rxBuffer);
        // Update led status
        updateLedState(ledBrightness, ledColor);
      }
      xSemaphoreGive(loraMutex);
    }
    
    // Small delay to yield CPU; adjust if you want more aggressive polling
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

// ------------ LoRa TX Task (every 15 ms) ------------
void LoRaTxTask(void *pvParameters) {
  (void) pvParameters;

  uint32_t counter = 0;

  for (;;) {
    // Get power data from power meter module
    voltage = ina219.getBusVoltage_V();
    current = ina219.getCurrent_mA();
    power = ina219.getPower_mW();

    // Get motion data
    isMotion = digitalRead(MOTION_SENSOR_PIN) == LOW ? true : false;
    
    // Get rain data
    isRain = digitalRead(RAIN_SENSOR_PIN) == HIGH ? true : false;
    
    // Get light value from light sensor
    ambientLightIntensity = getLightIntensity();
    
    // ambientLightIntensity = random(0, 100);

    char* stringToSend = buildJsonMessage(deviceID, ambientLightIntensity, ledBrightness, voltage, current, power, isMotion, isRain);
    if (xSemaphoreTake(loraMutex, portMAX_DELAY) == pdTRUE) {
      LoRa.beginPacket();
      LoRa.print(stringToSend);
      // LoRa.print(counter);
      LoRa.endPacket();       // blocking until finished sending
      xSemaphoreGive(loraMutex);

      Serial.print("[TX] Sent packet #");
      Serial.print(counter);
      Serial.println(stringToSend);
      counter++;
    }

    // Send every 15 ms
    vTaskDelay(pdMS_TO_TICKS(10000));
  }
}

// ------------ Heartbeat Task (debug / 3rd task) ------------
void HeartbeatTask(void *pvParameters) {
  (void) pvParameters;

  // pinMode(LED_BUILTIN, OUTPUT);

  for (;;) {
    // digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); // toggle LED
    // Serial.println("[HB] System alive");
    isMotion = digitalRead(MOTION_SENSOR_PIN) == LOW ? true : false;
    isRain = digitalRead(RAIN_SENSOR_PIN) == HIGH ? true : false;
    if (isMotion == true || isRain == true) {
      char* stringToSend = buildJsonMessage(deviceID, ambientLightIntensity, ledBrightness, voltage, current, power, isMotion, isRain);
      if (xSemaphoreTake(loraMutex, portMAX_DELAY) == pdTRUE) {
        LoRa.beginPacket();
        LoRa.print(stringToSend);
        // LoRa.print(counter);
        LoRa.endPacket();       // blocking until finished sending
        xSemaphoreGive(loraMutex);

        Serial.print("[TX] Sent packet #");
        // Serial.print(counter);
        Serial.println(stringToSend);
        // counter++;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(1000));  // 1 second
  }
}

// ------------ Arduino setup ------------
void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("ESP32 LoRa + FreeRTOS demo");

  pinMode(MOTION_SENSOR_PIN, INPUT);
  pinMode(RAIN_SENSOR_PIN, INPUT);

  // Create mutex for LoRa access
  loraMutex = xSemaphoreCreateMutex();
  if (loraMutex == NULL) {
    Serial.println("Failed to create LoRa mutex!");
    while (1) { delay(1000); }
  }

  // LoRa pin config
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("Starting LoRa failed!");
    while (1) { delay(1000); }
  }
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(250E3);
  LoRa.setCodingRate4(5);
  LoRa.enableCrc();
  LoRa.setTxPower(10);
  Serial.println("LoRa initialized.");

  // Set up for DFRobot INA219
  Wire.begin(4, 5); // 4: SDA, 5: SCL
  while (ina219.begin() != true) {
    Serial.println("INA219 begin failed, check wiring or I2C address...");
    delay(2000);
  }

  ina219.linearCalibrate(ina219Reading_mA, extMeterReading_mA);
  Serial.println("IAN219 ready.\n");

  // Initialize RGB Led
  pixels.begin();
  updateLedState(ledBrightness, ledColor);

  // Create LoRa receive task
  xTaskCreatePinnedToCore(
    LoRaRxTask,
    "LoRa RX Task",
    4096,
    NULL,
    2,                // priority
    &loraRxTaskHandle,
    0                 // core 0
  );

  // Create LoRa send task
  xTaskCreatePinnedToCore(
    LoRaTxTask,
    "LoRa TX Task",
    4096,
    NULL,
    2,
    &loraTxTaskHandle,
    1                 // core 1
  );

  xTaskCreatePinnedToCore(
    HeartbeatTask,
    "Heartbeat Task",
    2048,
    NULL,
    1,
    &heartbeatTaskHandle,
    1
  );
}

void loop() {
  // You can leave this empty, or use it as a 4th task.
  // It runs as its own FreeRTOS task too.

  // Serial.print("BusVoltage:   ");
  // Serial.print(ina219.getBusVoltage_V(), 2);
  // Serial.println("V");
  // Serial.print("ShuntVoltage: ");
  // Serial.print(ina219.getShuntVoltage_mV(), 3);
  // Serial.println("mV");
  // Serial.print("Current:      ");
  // Serial.print(ina219.getCurrent_mA(), 1);
  // Serial.println("mA");
  // Serial.print("Power:        ");
  // Serial.print(ina219.getPower_mW(), 1);
  // Serial.println("mW");
  // Serial.println("");

  vTaskDelay(pdMS_TO_TICKS(1000));
}