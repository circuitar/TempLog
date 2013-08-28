/*
This program clears up the EEPROM used by the TempLog project.

Copyright (c) 2013 Circuitar
This software is released under the MIT license. See the attached LICENSE file for details.
*/
#include <Wire.h>
#include "Nanoshield_EEPROM.h"

Nanoshield_EEPROM eeprom(0, 0, 0);

void setup() {
  Serial.begin(115200);
  Serial.println("-------------------------------");
  Serial.println(" Nanoshield Temperature Logger");
  Serial.println("-------------------------------");
  Serial.println("");
  Serial.print("Resetting EEPROM... ");

  // Initialize EEPROM
  eeprom.begin();
  
  // Reset EEPROM counter
  if (eeprom.write(0, (byte)0, 4) == 4) {
    Serial.print("Done!");
  } else {
    Serial.print("Failed");
  }
}

void loop() {}

