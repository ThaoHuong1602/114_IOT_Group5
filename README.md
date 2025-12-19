# 114_IOT_Group5 - 💡 Smart Street Light System
This GitHub repository contains the materials for the IoT project developed by Group 5.

# 🌟 Project Overview
This project implements a Smart Street Lighting System leveraging Internet of Things (IoT) technology to optimize public illumination and energy management in a Smart City context. It addresses key disadvantages of traditional street lighting, such as high energy consumption (up to 40% of a municipality's electricity bill) , fixed operation resulting in wasted energy , and higher maintenance costs.

# 🎯  Key System Features

Adaptive Illumination: 
  Lights adjust intensity based on real-time environmental data collected from sensors (Infrared Motion , Ambient Light , Rain ).

Predictive Maintenance (PdM):
  Utilizes power consumption data (measured by the INA219 module ) and other parameters (Temperature, Voltage, Light output) to estimate Remaining Useful Life (RUL) and predict potential failures.

Centralized Control & Monitoring:
  Data is collected at 5-minute intervals and managed via a comprehensive Web Interface  (ThingsBoard) for status monitoring and manual control.

# 🏗️ System Architecture & Technology Stack
The system follows a layered Modern Street Light System architecture:
1. End Device 
Hardware: EPS32 Development Board (MCU) for cost-effective performance in multi-sensor data processing.
Sensors: Infrared Motion (SEN0018) , Ambient Light (GY-30 BH1750FVI) , Rain Sensor , and Power Meter (INA219).
Communication: LoRa-Enable Modules for low-power, long-range transmission.

2. Gateway 
Hardware: Raspberry Pi 3B acting as the LoRaWAN Gateway.
Software: Python scripts running on Raspberry Pi OS to receive LoRa packets and forward them to the server.

3. Network Server & Application 
Network Server: ChirpStack manages, authenticates, and decodes raw LoRa data.
Database: Data storage utilizing InfluxDB and PostgreSQL.
IoT Platform: ThingsBoard is used as the Web Interface for real-time telemetry, maintenance alerts, and system control.

🛠 Key Technologies

Microcontrollers: ESP32-WROOM-32 (End Nodes), Raspberry Pi 3/4 (Gateway).
Sensors: KY-032 PIR Motion, TCRT5000 Light Sensor, Rain Sensor, Watt Power Meter.

Communication:

LoRa: Long-range communication between Street Lights and Gateway (inAir9B module).
MQTT: Telemetry transport from Gateway to Cloud.
Platform: ThingsBoard (Community Edition) for visualization and device management.
AI/ML: Predictive maintenance model for anomaly detection.

🏗 System Architecture
Data Flow: Sensors → ESP32 (Node) → LoRa (Radio) → Raspberry Pi (Gateway) → MQTT → ThingsBoard (Cloud)

End Device Layer: ESP32 collects data (Light intensity, Rain status, Power usage) and controls the LED driver.

Gateway Layer: Raspberry Pi receives LoRa packets via SPI and forwards them to ThingsBoard via MQTT.

Application Layer: ThingsBoard dashboard visualizes "Light Intensity," "Maintenance Alerts," and "Power Consumption".

⚡ Getting Started
Prerequisites
**Hardware:**
ESP32 Dev Module
Raspberry Pi (Zero W / 3 / 4)
LoRa Modules (e.g., inAir9B or RA-02)
Sensors: Rain, PIR (KY-032), Light (TCRT5000)

**Software:**
Arduino IDE
Python 3.7+ (for Gateway)
ThingsBoard (Live Demo or Local Install)


**Step 1: Hardware Setup & Assembly**
1.1 LoRa Gateway (Raspberry Pi) Connect the LoRa module to the Raspberry Pi GPIO headers as follows:
<img width="410" height="415" alt="image" src="https://github.com/user-attachments/assets/04005291-f368-472a-92eb-66f3371d9b24" />

1.2 End Node (ESP32) Assemble the 3D printed street light components. Wire the sensors to the ESP32 analog/digital pins as defined in firmware/street_light_node/config.h.

Step 2: Firmware Installation
Open firmware/street_light_node.ino in Arduino IDE.
Install the required LoRa library (e.g., Sandeep Mistry LoRa).
Update the LoRa Frequency (433MHz/868MHz/915MHz) to match your region.
Upload to the ESP32.

Step 3: Gateway Configuration
SSH into your Raspberry Pi.
Navigate to the gateway directory and install dependencies:
_cd gateway
pip install RPi.GPIO spidev paho-mqtt_
Update gateway_config.py with your ThingsBoard Device Access Token.
Run the gateway:
_python gateway_service.py_

Step 4: ThingsBoard Dashboard
Login to ThingsBoard.
Go to Dashboards > Import.
Upload thingsboard/dashboard_export.json.
You should now see the "Smart LED Management" interface with widgets for:
Total Lights / Working Lights count.
Real-time Light Intensity graph.
Predictive Maintenance Alerts.
