TempLog
=======

This is a project used to monitor temperature using a thermocouple and logging it in EEPROM along with date and time taken from an RTC.

This was built and tested using Nanoshields from http://www.circuitar.com.br

There are 3 subdirectories:
- TempLog: this contains the main Arduino sketch for the TempLog project.
- TempLogPlot: this is a python software used to plot the data collected from TempLog in real time. It is useful as a general visualization tool.
- TempLogReset: a simple sketch to wipe out the EEPROM and clear all stored data.

To run this project you will need the following Arduino libraries (all on github):
- Nanoshield_RTC
- Nanoshield_EEPROM
- Adafruit_MAX31855

---

Copyright (c) 2013 Circuitar

This software is released under an MIT license. See the attached LICENSE file for details.
