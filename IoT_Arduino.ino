#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ================= USER CONFIGURATION =================
const char* ssid     = "Converge_2.4GHz_Yqc8";      
const char* password = "V2m48Z3p"; 

// REPLACE 192.168.X.X with your laptop's IPv4 Address
const char* serverUrl = "http://192.168.100.6:8000/telemetry";
const char* apiKey    = "SHANIA_PROACTIVE_2026_SECRET"; 

// ================= HARDWARE PINS (CONFIRMED) =================
#define DHTPIN 4
#define DHTTYPE DHT22

// Mapped based on diagnostic test:
const int greenLed = 18;  // Confirmed Green
const int yellowLed = 19; // Confirmed Yellow/Orange
const int redLed = 21;    // Confirmed Red

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  delay(1000); 

  // 1. Setup Hardware
  pinMode(greenLed, OUTPUT);
  pinMode(yellowLed, OUTPUT);
  pinMode(redLed, OUTPUT);
  
  // ================= STARTUP LOGIC: RED FIRST =================
  // Explicitly turn off Green/Yellow and turn ON Red.
  digitalWrite(greenLed, LOW);
  digitalWrite(yellowLed, LOW);
  digitalWrite(redLed, HIGH); 
  // ============================================================

  dht.begin();
  Serial.println("System Started. Default State: RED (IDLE).");

  // 2. Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
}

void loop() {
  // 3. Read Sensor
  float hum = dht.readHumidity();
  float temp = dht.readTemperature(); 

  // Check for sensor failure
  if (isnan(hum) || isnan(temp)) {
    Serial.println("❌ Failed to read from DHT sensor!");
    // Rapid Red Blink = Hardware Error
    digitalWrite(redLed, LOW); delay(100); digitalWrite(redLed, HIGH); delay(100);
    return;
  }

  // 4. Send Data to Python AI
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    String url = String(serverUrl) + "?temp=" + String(temp, 1) + "&hum=" + String(hum, 1);
    
    Serial.print("Sending to AI: ");
    Serial.println(url);

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("x-api-key", apiKey);

    int httpResponseCode = http.POST("");

    // 5. Handle AI Response
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("✅ AI Response: " + response);

      StaticJsonDocument<512> doc;
      DeserializationError error = deserializeJson(doc, response);

      if (!error) {
        const char* command = doc["command"]; 
        updateLEDs(command);
      } else {
        Serial.print("JSON Parse Failed: ");
        Serial.println(error.c_str());
      }
    } else {
      Serial.print("❌ HTTP Error: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("❌ WiFi Disconnected");
  }

  // Wait 5 seconds before next reading
  delay(5000); 
}

// Updates LEDs based on Python AI Command
void updateLEDs(String cmd) {
  // Reset all first
  digitalWrite(greenLed, LOW);
  digitalWrite(yellowLed, LOW);
  digitalWrite(redLed, LOW);

  if (cmd == "GREEN_ON") {
    digitalWrite(greenLed, HIGH); // Active Cooling
  } 
  else if (cmd == "RED_ON") {
    digitalWrite(redLed, HIGH);   // Idle/Stable
  } 
  else if (cmd == "YELLOW_BLINK") {
    // Prediction Warning: Blink then Hold
    for(int i=0; i<4; i++) {
      digitalWrite(yellowLed, HIGH); delay(200);
      digitalWrite(yellowLed, LOW); delay(200);
    }
    digitalWrite(yellowLed, HIGH); 
  }
}