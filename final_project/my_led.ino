void updateLedState(int ledBrightness, int ledColor) {
  printf("Update led status\n");
  // Set brightness
  pixels.setBrightness(ledBrightness); // 0-255
  // Set color (1: yellow 0: white)
  if (ledColor == 1) {
    for (int i = 0; i < NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(255, 255, 0));
    }
    pixels.show();
  }
  else if (ledColor == 0) {
    for (int i = 0; i < NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(255, 255, 255)); // R, G, B
    }
    pixels.show();
  }
}