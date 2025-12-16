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

