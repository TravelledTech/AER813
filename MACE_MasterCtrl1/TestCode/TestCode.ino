/* * MACE PROJECT - SERIAL STABILITY TEST
 * Use this to verify Python is sending <Angle,Velocity> correctly.
 */

// Global control variables (static-like persistence)
float targetAng = 0.0;
float targetVel = 0.0;
float Kp = 0.0, Ki = 0.0, Kd = 0.0;

unsigned long lastBlink = 0;
bool ledState = false;

void setup() {
  Serial.begin(115200);
  
  // CRITICAL: Low timeout prevents the loop from "freezing" 
  // if a character is lost during your walk.
  Serial.setTimeout(5); 
  
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println("SYSTEM_READY");
}

void loop() {
  // 1. Check if data is waiting in the "pipe"
  if (Serial.available() > 0) {
    
    // Peek at the first character to see what kind of data it is
    char startChar = Serial.peek();

    if (startChar == '<') {
      // --- PACKET TYPE: <Angle,Velocity> ---
      Serial.read();                // Toss the '<'
      targetAng = Serial.parseFloat(); 
      targetVel = Serial.parseFloat();
      
      // Blink LED to show we got a high-speed vision packet
      digitalWrite(LED_BUILTIN, HIGH);
      lastBlink = millis();
    } 
    else if (startChar == 'P' || startChar == 'I' || startChar == 'D') {
      // --- PACKET TYPE: Gain Updates ---
      char label = Serial.read();
      float val = Serial.parseFloat();
      
      if (label == 'P') Kp = val;
      if (label == 'I') Ki = val;
      if (label == 'D') Kd = val;
      
      // Double blink or print to show gain update received
      Serial.print("GAIN_UPDATE: "); Serial.print(label); Serial.println(val);
    }
    else {
      // --- JUNK DATA / NEWLINES ---
      // If we see a '\n', '>', or random noise, toss it to keep the pipe clear.
      Serial.read(); 
    }
  }

  // 2. Clear the LED after 20ms so it looks like a flicker
  if (millis() - lastBlink > 20) {
    digitalWrite(LED_BUILTIN, LOW);
  }

  // 3. YOUR PID LOGIC GOES HERE
  // For now, we just wait. The loop stays fast!
}