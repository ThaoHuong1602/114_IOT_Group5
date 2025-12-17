uint8_t getLightIntensity() {
  int rawValue = analogRead(LIGHT_SENSOR_PIN);
  uint8_t brightnessPercent = map(4095 - rawValue, 0, 4095, 0, 100);
  return brightnessPercent;
}