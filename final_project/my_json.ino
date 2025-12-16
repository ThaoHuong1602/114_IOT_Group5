// This function builds a JSON string to send
char* buildJsonMessage(
  uint8_t deviceID, 
  uint8_t ambientLightIntensity,
  uint8_t ledBrightness,
  uint8_t voltage,
  uint8_t current,
  uint8_t power,
  bool isMotion,
  bool isRain) {
    cJSON* root = cJSON_CreateObject();

    cJSON_AddNumberToObject(root, "deviceID", deviceID);
    cJSON_AddNumberToObject(root, "ambientLightIntensity", ambientLightIntensity);
    cJSON_AddNumberToObject(root, "ledBrightness", ledBrightness);
    cJSON_AddNumberToObject(root, "voltage", voltage);
    cJSON_AddNumberToObject(root, "current", current);
    cJSON_AddNumberToObject(root, "power", power);
    cJSON_AddBoolToObject(root, "isMotion", isMotion);
    cJSON_AddBoolToObject(root, "isRain", isRain);

    char* jsonString = cJSON_PrintUnformatted(root);  // compact JSON
    cJSON_Delete(root);

    return jsonString;  // caller MUST free()
}

// This function parse a JSON string to a JSON
void parseJsonMessage(const char* jsonString) {
    cJSON* root = cJSON_Parse(jsonString);

    if (!root) {
        printf("Receiver: JSON parse error!\n");
        return;
    }

    cJSON* deviceID = cJSON_GetObjectItem(root, "deviceID");
    cJSON* ambientLightIntensity = cJSON_GetObjectItem(root, "ambientLightIntensity");
    cJSON* ledBrightness = cJSON_GetObjectItem(root, "ledBrightness");
    cJSON* voltage = cJSON_GetObjectItem(root, "voltage");
    cJSON* current = cJSON_GetObjectItem(root, "current");
    cJSON* power = cJSON_GetObjectItem(root, "power");
    cJSON* isMotion = cJSON_GetObjectItem(root, "isMotion");
    cJSON* isRain = cJSON_GetObjectItem(root, "isRain");

    if (deviceID && ambientLightIntensity && ledBrightness && voltage && current && power && isMotion && isRain) {
        printf("Receiver: deviceID = %d\n", deviceID->valueint);
        printf("Receiver: ambientLightIntensity = %d\n", ambientLightIntensity->valueint);
        printf("Receiver: ledBrightness = %d\n", ledBrightness->valueint);
        printf("Receiver: voltage = %d\n", voltage->valueint);
        printf("Receiver: current = %d\n", current->valueint);
        printf("Receiver: power = %d\n", power->valueint);
        if (cJSON_IsBool(isMotion)) {
          if (cJSON_IsTrue(isMotion)) printf("isMotion: true\n");
          else printf("isMotion: false\n");
        }
        if (cJSON_IsBool(isRain)) {
          if (cJSON_IsTrue(isRain)) printf("isRain: true\n");
          else printf("isRain: false\n");
        }
    }     
    else {
        printf("Receiver: Missing fields!\n");
    }

    cJSON_Delete(root);
}