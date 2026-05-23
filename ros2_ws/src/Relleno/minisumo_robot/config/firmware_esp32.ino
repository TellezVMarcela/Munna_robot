/*
 * Firmware ESP32 / Arduino para robot Minisumo
 * ================================================
 * Compatible con: Arduino Mega, ESP32, Arduino Nano
 *
 * PINOUT (ajustar según tu hardware):
 *   Motor Izquierdo:  IN1=2, IN2=3, ENA=9  (PWM)
 *   Motor Derecho:    IN3=4, IN4=5, ENB=10 (PWM)
 *   Sensor IR Izq:    A0
 *   Sensor IR Centro: A1
 *   Sensor IR Der:    A2
 *   Sensor Borde FL:  6   (digital – HIGH = borde)
 *   Sensor Borde FR:  7
 *   Sensor Borde BL:  8
 *   Sensor Borde BR:  11
 *
 * PROTOCOLO SERIAL (con ROS2):
 *   Recibe:  "L<pwm> R<pwm>\n"    ej: "L200 R-150\n"
 *   Envía:   "OPP:<izq>,<centro>,<der> EDGE:<FL>,<FR>,<BL>,<BR>\n"
 *            ej: "OPP:0.45,0.12,0.80 EDGE:0,0,0,0\n"
 *
 * Distancia IR: se asume sensor GP2Y0A21 (10–80 cm)
 *   Fórmula: dist_cm = 4800 / (ADC_value - 20)
 */

// ─── Pines motores ──────────────────────────────────────────────────────────
const int IN1 = 2, IN2 = 3, ENA = 9;   // Motor izquierdo
const int IN3 = 4, IN4 = 5, ENB = 10;  // Motor derecho

// ─── Pines sensores IR oponente ─────────────────────────────────────────────
const int IR_LEFT   = A0;
const int IR_CENTER = A1;
const int IR_RIGHT  = A2;

// ─── Pines sensores de borde ────────────────────────────────────────────────
const int EDGE_FL = 6;
const int EDGE_FR = 7;
const int EDGE_BL = 8;
const int EDGE_BR = 11;

// ─── Parámetros ─────────────────────────────────────────────────────────────
const int   SERIAL_BAUD    = 115200;
const int   CMD_TIMEOUT_MS = 500;   // ms sin cmd → stop motores
const int   SENSOR_HZ      = 20;    // frecuencia de publicación de sensores
const float MAX_DIST_M     = 1.0;   // distancia máxima de sensores IR (m)

// ─── Variables globales ──────────────────────────────────────────────────────
unsigned long lastCmdMs  = 0;
unsigned long lastSendMs = 0;
int           leftPWM    = 0;
int           rightPWM   = 0;

// ────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(SERIAL_BAUD);

  // Motores
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT); pinMode(ENA, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT); pinMode(ENB, OUTPUT);
  stopMotors();

  // Sensores borde
  pinMode(EDGE_FL, INPUT);
  pinMode(EDGE_FR, INPUT);
  pinMode(EDGE_BL, INPUT);
  pinMode(EDGE_BR, INPUT);

  Serial.println("# Minisumo firmware OK");
}

// ────────────────────────────────────────────────────────────────────────────
void loop() {
  // 1. Leer comandos seriales
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.startsWith("L")) {
      parseMotorCmd(line);
      lastCmdMs = millis();
    }
  }

  // 2. Watchdog: detener si no llegan comandos
  if (millis() - lastCmdMs > CMD_TIMEOUT_MS) {
    leftPWM = rightPWM = 0;
    stopMotors();
  } else {
    setMotors(leftPWM, rightPWM);
  }

  // 3. Publicar sensores a 20 Hz
  if (millis() - lastSendMs >= (1000 / SENSOR_HZ)) {
    sendSensorData();
    lastSendMs = millis();
  }
}

// ─── Parser de comandos motor ────────────────────────────────────────────────
void parseMotorCmd(const String& line) {
  // Formato: "L200 R-150"
  int l_idx = line.indexOf('L');
  int r_idx = line.indexOf('R');
  if (l_idx < 0 || r_idx < 0) return;

  leftPWM  = line.substring(l_idx + 1, r_idx).toInt();
  rightPWM = line.substring(r_idx + 1).toInt();

  // Clamp
  leftPWM  = constrain(leftPWM,  -255, 255);
  rightPWM = constrain(rightPWM, -255, 255);
}

// ─── Control de motores ──────────────────────────────────────────────────────
void setMotors(int left, int right) {
  // Motor izquierdo
  if (left > 0) {
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  } else if (left < 0) {
    digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH);
  } else {
    digitalWrite(IN1, LOW);  digitalWrite(IN2, LOW);
  }
  analogWrite(ENA, abs(left));

  // Motor derecho
  if (right > 0) {
    digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  } else if (right < 0) {
    digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH);
  } else {
    digitalWrite(IN3, LOW);  digitalWrite(IN4, LOW);
  }
  analogWrite(ENB, abs(right));
}

void stopMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);    analogWrite(ENB, 0);
}

// ─── Lectura y envío de sensores ─────────────────────────────────────────────
void sendSensorData() {
  // Sensores IR oponente → distancia en metros
  float dL = irToMeters(analogRead(IR_LEFT));
  float dC = irToMeters(analogRead(IR_CENTER));
  float dR = irToMeters(analogRead(IR_RIGHT));

  // Sensores de borde (HIGH = fuera del dohyo)
  int eFL = digitalRead(EDGE_FL);
  int eFR = digitalRead(EDGE_FR);
  int eBL = digitalRead(EDGE_BL);
  int eBR = digitalRead(EDGE_BR);

  Serial.print("OPP:");
  Serial.print(dL, 2); Serial.print(",");
  Serial.print(dC, 2); Serial.print(",");
  Serial.print(dR, 2);

  Serial.print(" EDGE:");
  Serial.print(eFL); Serial.print(",");
  Serial.print(eFR); Serial.print(",");
  Serial.print(eBL); Serial.print(",");
  Serial.println(eBR);
}

// ─── Conversión ADC → metros (GP2Y0A21) ──────────────────────────────────────
float irToMeters(int adc) {
  if (adc < 20) return MAX_DIST_M;
  float dist_cm = 4800.0f / (float)(adc - 20);
  float dist_m  = dist_cm / 100.0f;
  return constrain(dist_m, 0.05f, MAX_DIST_M);
}
