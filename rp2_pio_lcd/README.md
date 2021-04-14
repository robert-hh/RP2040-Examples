# Character LCD driver using the RP2 PIO

This is a driver for the LCD lib of Dave Hylands. It uses the PIO mode of the RP2 
for the 4 or 8 bit parallel interface of a LCD. The driver keeps the structure of
Dave Hylands drivers. The advantage over the GPIO variants migh be small. But 
it demonstrates the capability of the PIO for driving the enable signal and splitting
up the 8 bit data into nibbles.
