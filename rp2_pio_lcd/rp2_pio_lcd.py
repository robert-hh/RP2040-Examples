"""Implements a HD44780 character LCD connected via ESP32 GPIO pins."""

from lcd_api import LcdApi
from machine import Pin
from utime import sleep_ms, sleep_us
import rp2

class PIOLcd(LcdApi):
    """Implements a HD44780 character LCD connected via ESP32 GPIO pins."""

    def __init__(self, rs_pin, enable_pin=None, data_port=None, fourbit=True,
                 rw_pin=None, backlight_pin=None,
                 num_lines=2, num_columns=16):
        """Constructs the PIOLcd object. The xx_pin arguments must be machine.Pin
        objects. data_port is the number of the lowest order GPIO pin for data, which must
        be consecutive. fourbit tells, whether the display is connected in 4-bit or 8-bit mode.
        enable_pin is the GPIO number of the enable pin.
        The rw pin isn't used by this library, but if you specify it, then
        it will be set low.
        """
        self.rs_pin = rs_pin
        self.rw_pin = rw_pin
        self.backlight_pin = backlight_pin
        self._4bit = fourbit
        self.rs_pin.init(Pin.OUT)
        self.rs_pin.value(0)
        if self.rw_pin:
            self.rw_pin.init(Pin.OUT)
            self.rw_pin.value(0)
        if self.backlight_pin is not None:
            self.backlight_pin.init(Pin.OUT)
            self.backlight_pin.value(0)

        # activate the four bit state machine in single nibble mode
        self.sm = rp2.StateMachine(0, self._4bit_write, freq=1000000,
                        sideset_base=enable_pin, out_base=data_port, pull_thresh=4)
        self.sm.active(1)

        sleep_ms(20)   # Allow LCD time to powerup
        # Send reset 3 times
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(5)    # need to delay at least 4.1 msec
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(1)
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(1)
        cmd = self.LCD_FUNCTION
        if not self._4bit:
            cmd |= self.LCD_FUNCTION_8BIT
        self.hal_write_init_nibble(cmd)
        sleep_ms(1)

        if self._4bit is True:
            # switch to dual níbble mode mode by overriding pull_thresh
            self.sm.active(0)
            self.sm = rp2.StateMachine(0, self._4bit_write, freq=1000000,
                            sideset_base=enable_pin, out_base=data_port, pull_thresh=8)
            self.sm.active(1)
        else:
            # switch the state machine to 8 bit
            self.sm.active(0)
            self.sm = rp2.StateMachine(0, self._8bit_write, freq=1000000,
                            sideset_base=enable_pin, out_base=data_tbase)
            self.sm.active(1)

        LcdApi.__init__(self, num_lines, num_columns)
        if num_lines > 1:
            cmd |= self.LCD_FUNCTION_2LINES
        self.hal_write_command(cmd)

    # PIO code for 8 bit output
    @rp2.asm_pio(
        sideset_init=(rp2.PIO.OUT_LOW,),
        out_init=(rp2.PIO.OUT_LOW,) * 8,
        out_shiftdir=rp2.PIO.SHIFT_LEFT,
        autopull=True,
        pull_thresh=8)
    def _8bit_write():
        # fmt: off
        out(pins, 8)            .side(1)
        nop()                   .side(0)
        # fmt: on

    # PIO code for 4 bit output
    @rp2.asm_pio(
        sideset_init=(rp2.PIO.OUT_LOW,),
        out_init=(rp2.PIO.OUT_LOW,) * 4,
        out_shiftdir=rp2.PIO.SHIFT_LEFT,
        autopull=True,
        pull_thresh=4)
    def _4bit_write():
        # fmt: off
        out(pins, 4)            .side(1)
        nop()                   .side(0)
        # fmt: on

    def hal_write_init_nibble(self, nibble):
        """Writes an initialization nibble to the LCD.
        This particular function is only used during initialization.
        """
        self.sm.put(nibble, 24)

    def hal_backlight_on(self):
        """Allows the hal layer to turn the backlight on."""
        if self.backlight_pin:
            self.backlight_pin.value(1)

    def hal_backlight_off(self):
        """Allows the hal layer to turn the backlight off."""
        if self.backlight_pin:
            self.backlight_pin.value(0)

    def hal_write_command(self, cmd):
        """Writes a command to the LCD.
        Data is latched on the falling edge of E.
        """
        self.rs_pin.value(0)
        self.hal_write_8bits(cmd)
        if cmd <= 3:
            # The home and clear commands require a worst
            # case delay of 4.1 msec
            sleep_ms(5)

    def hal_write_data(self, data):
        """Write data to the LCD."""
        self.rs_pin.value(1)
        self.hal_write_8bits( data)

    def hal_write_8bits(self, value):
        """Writes 8 bits of data to the LCD."""
        if self.rw_pin:
            self.rw_pin.value(0)
        self.sm.put(value, 24)

