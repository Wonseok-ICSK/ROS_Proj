/*
 * MRS-10G V2.0 Test & EVK
 * SeungJin Hwang, villiv micron inc., 2020.08.12
 *
 * A1은 센서 전원 활성화, A2는 측정값 준비 신호다.
 * 9600 baud에서 한 줄에 감지(1) 또는 미감지(0)를 보낸다.
 */
#include <Wire.h>

constexpr uint8_t SENSOR_ADDRESS = 0x0A;
constexpr uint8_t LDO_ENABLE = A1;
constexpr uint8_t RADAR_ISR = A2;

// false는 radar.ino, true는 sketch_dec12a.ino에 쓰이던 설정이다.
constexpr bool USE_DEC12_PROFILE = false;
constexpr uint16_t DETECTION_THRESHOLD = USE_DEC12_PROFILE ? 20 : 120;
constexpr unsigned long REPORT_DELAY_MS = USE_DEC12_PROFILE ? 300 : 0;
bool handledLow = false;

void setup() {
  Wire.begin();
  Serial.begin(9600);
  pinMode(LDO_ENABLE, OUTPUT);
  digitalWrite(LDO_ENABLE, HIGH);
  pinMode(RADAR_ISR, INPUT);
}

void loop() {
  // LOW 한 구간에 한 번만 읽는다. HIGH로 돌아오면 다음 측정을 받는다.
  if (digitalRead(RADAR_ISR) == HIGH) {
    handledLow = false;
    return;
  }
  if (handledLow) {
    return;
  }
  handledLow = true;

  Wire.beginTransmission(SENSOR_ADDRESS);
  Wire.write(0xF1);
  Wire.write(0xAB);
  // STOP 없이 곧바로 읽기 요청을 보내 같은 I²C 거래를 이어 간다.
  if (Wire.endTransmission(false) != 0) {
    return;
  }
  if (Wire.requestFrom(SENSOR_ADDRESS, static_cast<uint8_t>(2)) != 2) {
    return;
  }

  // 첫 바이트가 하위 8비트다. 임계값은 카드에 저장된 원시 측정값 기준이다.
  const uint8_t lowByteValue = Wire.read();
  const uint8_t highByteValue = Wire.read();
  const uint16_t measurement = (static_cast<uint16_t>(highByteValue) << 8) | lowByteValue;
  Serial.print(measurement <= DETECTION_THRESHOLD ? "1\n" : "0\n");
  if (REPORT_DELAY_MS > 0) {
    delay(REPORT_DELAY_MS);
  }
}
