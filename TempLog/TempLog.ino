/*
This is the software for the TempLog project.

TempLog periodically gets a temperature reading from the Thermocouple Nanoshield, collects the time read from the
RTCMem Nanoshield, bundles it into a record and stores it into the I2C EEPROM available in the RTCMem Nanoshield.
The time interval between the readings, in milliseconds, can be set in constant SAMPLING_INTERVAL.

Copyright (c) 2013 Circuitar
This software is released under the MIT license. See the attached LICENSE file for details.
*/
#include <Wire.h>
#include <stdio.h>
#include "Adafruit_MAX31855.h"
#include "Nanoshield_EEPROM.h"
#include "Nanoshield_RTC.h"

// Define the temperature sampling interval in milliseconds
#define SAMPLING_INTERVAL 60000

// EEPROM record size in bytes
#define RECORD_SIZE 9

// Maximum number of records
#define MAX_RECORDS 3640

Adafruit_MAX31855 thermocouple(13, 8, 12);
Nanoshield_EEPROM eeprom(0, 0, 0);
Nanoshield_RTC rtc;
unsigned int nextRecord;
unsigned int usedRecords;

void setup()
{
  Serial.begin(115200);
  Serial.println("-------------------------------");
  Serial.println(" Nanoshield Temperature Logger");
  Serial.println("-------------------------------");
  Serial.println("");
  Serial.println("Record,Date,Time,Internal,External");

  // Initialize EEPROM and RTC
  eeprom.begin();
  rtc.begin();
  
  // Delay to let thermocouple stabilize
  delay(500);

  // Dump the used EEPROM records onto the serial port in CSV format
  usedRecords = getUsedRecords();
  for (unsigned int i = 0; i < usedRecords; i++) {
    printRecord(i);
  }
  
  // Initialize the next record variable
  nextRecord = getNextRecord();
}

void loop()
{
  // Keep saving records to EEPROM and printing the into the serial port
  rtc.read();
  saveRecord(
    nextRecord,
    rtc.getSeconds(),
    rtc.getMinutes(),
    rtc.getHours(),
    rtc.getDay(),
    rtc.getWeekday(),
    rtc.getMonth(),
    rtc.getYear(),
    thermocouple.readInternal(),
    thermocouple.readCelsius()
  );
  printRecord(nextRecord++);
  
  // Update number of used records
  if (nextRecord > usedRecords) usedRecords = nextRecord;

  // Go back to position zero if number of records overflows
  if (nextRecord >= MAX_RECORDS) nextRecord = 0;

  // Save the next and used position counters in the EEPROM
  byte buf[4];
  buf[0] = usedRecords >> 8;
  buf[1] = usedRecords;
  buf[2] = nextRecord >> 8;
  buf[3] = nextRecord;
  eeprom.write(0, buf, 4);

  // Wait for next sample
  delay(SAMPLING_INTERVAL);
}

unsigned int getUsedRecords()
{
  unsigned int used;
  
  // Get next available record
  while (!eeprom.startReading(0)) {
    delay(1);
  }
  used = eeprom.read() << 8;
  used |= eeprom.read();
  
  return used;
}

unsigned int getNextRecord()
{
  unsigned int next;
  
  // Get next available record
  while (!eeprom.startReading(2)) {
    delay(1);
  }
  next = eeprom.read() << 8;
  next |= eeprom.read();
  
  return next;
}

void printRecord(int pos)
{
  int sec, min, hour, day, wday, mon, year;
  unsigned long t1, t2;
  byte record[RECORD_SIZE];
  char row[40];
  
  // Read record
  while (!eeprom.startReading(4 + pos*RECORD_SIZE)) {
    delay(1);
  }
  for (int i = 0; i < RECORD_SIZE; i++) {
    record[i] = eeprom.read();
  }
  
  // Extract values from EEPROM record
  sec  = record[0] >> 2;
  min  = (record[0] & 0x03) << 4 | record[1] >> 4;
  hour = (record[1] & 0x0F) << 1 | record[2] >> 7;
  day  = (record[2] & 0x7C) >> 2;
  wday = (record[2] & 0x03) << 1 | record[3] >> 7;
  mon  = (record[3] & 0x78) >> 3;
  year = ((record[3] & 0x03) << 5 | record[4] >> 3) + 1900;
  if (record[3] & 0x04) year += 100;
  t1   = ((unsigned long)(record[4] & 0x07) << 14) | (unsigned long)record[5] << 6 | (unsigned long)record[6] >> 2;
  t2   = ((unsigned long)(record[6] & 0x03) << 16) | (unsigned long)record[7] << 8 | (unsigned long)record[8];

  // Print as CSV row
  sprintf(row, "%d,%04d-%02d-%02d,%02d:%02d:%02d,%d.%02d,%d.%02d", pos, year, mon, day, hour, min, sec, (int)(t1/100) - 300, (int)(t1%100), (int)(t2/100) - 300, (int)(t2%100));
  Serial.println(row);
}

void saveRecord(unsigned int pos, byte sec, byte min, byte hour, byte day, byte wday, byte mon, unsigned int year, double temp1, double temp2)
{
  byte record[RECORD_SIZE];
  unsigned long t1, t2;
  byte century = 0;
  
  // Convert the temperatures to integer values
  // Unit is 1/100th of a degree Celsius, offset -300 degrees
  t1 = (unsigned long)((temp1 + 300) * 100.0);
  t2 = (unsigned long)((temp2 + 300) * 100.0);
  
  // Update the century bit and update year to 0-99 range
  if (year >= 2000) century = 1;
  year %= 100;
  
  // Convert parameters to record
  record[0] = sec << 2 | min >> 4;
  record[1] = min << 4 | hour >> 1;
  record[2] = hour << 7 | day << 2 | wday >> 1;
  record[3] = wday << 7 | mon << 3 | century << 2 | year >> 5;
  record[4] = year << 3 | (t1 >> 14 & 0x07);
  record[5] = t1 >> 6;
  record[6] = t1 << 2 | (t2 >> 16 & 0x03);
  record[7] = t2 >> 8;
  record[8] = t2;
  
  // Write record
  if (eeprom.write(4 + pos*RECORD_SIZE, record, RECORD_SIZE) != RECORD_SIZE) {
    Serial.println("Failed to save record to EEPROM");
  };
}

