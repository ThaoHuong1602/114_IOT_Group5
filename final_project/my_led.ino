void setColor(int red, int green, int blue) { 
  if (red == 0 && green == 0 && blue == 0) {
    digitalWrite(LED_COMMON_ANODE, LOW);
  }
  else {
    digitalWrite(LED_COMMON_ANODE, HIGH);
  }
  analogWrite(LED_RED, 255 - red);
  analogWrite(LED_GREEN, 255 - green);
  analogWrite(LED_BLUE, 255 - blue);
}