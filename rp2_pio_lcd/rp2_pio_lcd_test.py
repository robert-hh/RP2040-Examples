"""Implements a HD44780 character LCD connected via RP2040 GPIO pins using PIO."""

from machine import Pin
from rp2_pio_lcd import PIOLcd
from utime import sleep_ms, ticks_ms

# Wiring used for this example:
#
#  1 - Vss (aka Ground) - Connect to one of the ground pins on you pyboard.
#  2 - VDD - I connected to VIN which is 5 volts when your pyboard is powered via USB
#  3 - VE (Contrast voltage) - I'll discuss this below
#  4 - RS (Register Select) connect to GP11 (as per call to PIOLcd)
#  5 - RW (Read/Write) - CONNECT TO GROUND before applying power!
#  6 - EN (Enable) connect to GP10 (as per call to PIOLcd)
#  7 - D0 - leave unconnected
#  8 - D1 - leave unconnected
#  9 - D2 - leave unconnected
# 10 - D3 - leave unconnected
# 11 - D4 - connect to GP2 (as per call to PIOLcd)
# 12 - D5 - connect to GP3 (as per call to PIOLcd)
# 13 - D6 - connect to GP4 (as per call to PIOLcd)
# 14 - D7 - connect to GP5 (as per call to PIOLcd)
# 15 - A (BackLight Anode) - Connect to VIN
# 16 - K (Backlight Cathode) - Connect to Ground
#
# On 14-pin LCDs, there is no backlight, so pins 15 & 16 don't exist.
#
# The Contrast line (pin 3) typically connects to the center tap of a
# 10K potentiometer, and the other 2 legs of the 10K potentiometer are
# connected to pins 1 and 2 (Ground and VDD)
# 
# Since the LCD runs at 5V, it is ESSENTIAL to connect RW to Ground before applying 
# power to the LCD. That protects the GPIO pins of the RP2040 from overload.
#
# The wiring diagram on the following page shows a typical "base" wiring:
# http://www.instructables.com/id/How-to-drive-a-character-LCD-displays-using-DIP-sw/step2/HD44780-pinout/
# Add to that the EN, RS, and D4-D7 lines.


def test_main():
    """Test function for verifying basic functionality."""
    print("Running test_main")
    lcd = PIOLcd(rs_pin=Pin(11),
                 enable=Pin(10),
                 data_port=Pin(2),
                 fourbit=True,
                 num_lines=2, num_columns=16)
    lcd.putstr("It Works!\nSecond Line\nThird Line\nFourth Line")
    sleep_ms(3000)
    lcd.clear()
    count = 0
    while True:
        lcd.move_to(0, 0)
        lcd.putstr("%7d" % (ticks_ms() // 1000))
        sleep_ms(1000)
        count += 1
