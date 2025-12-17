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

    cJSON* deviceIdJson = cJSON_GetObjectItem(root, "deviceID");
    cJSON* cmdJson = cJSON_GetObjectItem(root, "CMD");
    cJSON* valJson = cJSON_GetObjectItem(root, "val");

    if (deviceIdJson && cmdJson && valJson) {
        printf("Receiver: deviceID = %d\n", deviceIdJson->valueint);
        deviceID = deviceIdJson->valueint;
        printf("Receiver: CMD = %s\n", cmdJson->valuestring);
        cmd = cmdJson->valuestring;
        printf("Receiver: val = %d\n", valJson->valueint);
        val = valJson->valueint;
    }     
    else {
        printf("Receiver: Missing fields!\n");
    }
    if (deviceID == 0) {
      if (cmd == "DIM") {
        ledBrightness = val;
      }
      else if (cmd == "COLOR") {
        ledColor = val;
      }
      else if (cmd == "AUTO") {
        operationMode = val;
      }
    }

    cJSON_Delete(root);
}