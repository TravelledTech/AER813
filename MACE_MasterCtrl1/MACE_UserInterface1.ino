#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

RF24 radio(7, 8); // CE, CSN
const byte address[6] = "00001";  // Address of RF24 radio channel

const uint8_t N = 3;   // Number of floating-point variables (measurements)
float payload[N];

#pragma pack(push, 1)
struct CmdAck {
  float theta_deg;   // set-point in degrees (human-friendly)
  float kp;          // outer loop Kp
  float ki;          // outer loop Ki
  float kd;          // outer loop Kd
  float kd_alpha;    // D filter alpha (0..1), if used
  uint8_t seq;       // bump when you change any field (optional)
};
#pragma pack(pop)

volatile CmdAck cmd = {0.0f, 0.8f, 0.05f, 0.10f, 0.10f, 0}; // sensible defaults

// Set-point in DEGREES that we’ll send back in ACK payloads
// (optional) clamp helper
static inline float clampf(float x, float lo, float hi){ return x<lo?lo:(x>hi?hi:x); }

void setup() {
  Serial.begin(115200);
  radio.begin();
  radio.setPALevel(RF24_PA_MIN);

  // Radio receiver configuration
  radio.openReadingPipe(0, address);
  radio.setAutoAck(true);
  radio.enableAckPayload();
  radio.startListening();

  // Queue initial command so TX can read immediately
  radio.writeAckPayload(0, &cmd, sizeof(cmd));

  Serial.println(F("Disp_MACE ready. Commands: T=<deg>, KP=<val>, KI=<val>, KD=<val>, KDA=<val>"));
}

void loop() {
  // ---- 1) Read telemetry from MACE (θ, ω, u_sat or similar) ----
  if (radio.available()) {
    while (radio.available()) {
      radio.read(payload, sizeof(payload));
    }
    Serial.print(millis()/1000.0, 3);
    Serial.print("\t");
    for (uint8_t i=0; i<N; ++i) {
      Serial.print(payload[i], 3);
      Serial.print("  ");
    }
    Serial.println();
  }

  // ---- 2) Parse a new theta setpoint from Serial (degrees) ----
  if (Serial.available()) {
    // Accept formats like: "T=15", "t= -10.5", or just "20"
    String s = Serial.readStringUntil('\n');
    s.trim();

    // Accept formats like "T=15", "KP=0.9", or even just "15" (treated as T)
    String up = s; up.toUpperCase();
    float v = 0.0f;
    bool changed = false;

    // int eq = s.indexOf('=');
    // if (eq >= 0) s = s.substring(eq + 1);
    // float v = s.toFloat();
    int eq = up.indexOf('=');
    String key = (eq>=0) ? up.substring(0, eq) : String("T");
    String val = (eq>=0) ? s.substring(eq+1) : s;  // keep original for float parsing
    v = val.toFloat();

    /* Set angle θ limits to +/- 180 degrees from the initial reference */
    if (key == "T") {
      cmd.theta_deg = clampf(v, -180.0f, 180.0f);
      changed = true;
    } else if (key == "KP") {
      cmd.kp = clampf(v, 0.0f, 10.0f);
      changed = true;
    } else if (key == "KI") {
      cmd.ki = clampf(v, 0.0f, 10.0f);
      changed = true;
    } else if (key == "KD") {
      cmd.kd = clampf(v, 0.0f, 10.0f);
      changed = true;
    } else if (key == "KDA") {
      cmd.kd_alpha = clampf(v, 0.0f, 1.0f);
      changed = true;
    }

    if (changed) {
      cmd.seq++;
      radio.writeAckPayload(0, &cmd, sizeof(cmd));
      Serial.print(F("[ACK queued] T=")); Serial.print(cmd.theta_deg,3);
      Serial.print(F("  Kp=")); Serial.print(cmd.kp,3);
      Serial.print(F("  Ki=")); Serial.print(cmd.ki,3);
      Serial.print(F("  Kd=")); Serial.print(cmd.kd,3);
      Serial.print(F("  KdA=")); Serial.println(cmd.kd_alpha,3);
    }
  }
}
