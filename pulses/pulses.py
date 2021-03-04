# Trial class to get and put pulse trains on a GPIO pin
# using PIO. The pulse duration is set or returned as
# the multiple of a basic tick, defined by the PIO clock,
# which gives a lot of flexibilty. Since the duration values
# used can be 32 bit integers, that gives a wide range of
# duration and resolution. The maximum frequency for timing
# pulses is machine.freq()/2, for sending pulses it's
# machine.freq(). So at 125MHz MCU clock
# for timing input pulses, the resolution can be 16ns
# for a pulse range of ~120ns - ~68 seconds, for sending
# the resolution can be 8 ns and the range ~60ns to ~34 seconds.
# At lower frequencies for the PIO, resolution and range
# scale accordingly.

import machine
import rp2
import time
import array


class Pulses:
    def __init__(self, get_pin=None, put_pin=None, sm_freq=1_000_000):
        self.get_done = False
        self.sm_get_nr = 0
        if get_pin is not None:
            if (sm_freq * 2) > machine.freq():
                raise (ValueError, "frequency too high")
            self.sm_get_freq = sm_freq * 2
            self.sm_get = rp2.StateMachine(self.sm_get_nr, self.sm_get_pulses,
                freq=self.sm_get_freq, jmp_pin=get_pin, in_base=get_pin,
                set_base=get_pin)
            self.sm_get.irq(self.irq_finished)
        else:
            self.sm_get = None

        self.put_done = False
        self.sm_put_nr = 4
        if put_pin is not None:
            if (sm_freq) > machine.freq():
                raise (ValueError, "frequency too high")
            self.sm_put_freq = sm_freq
            self.sm_put = rp2.StateMachine(self.sm_put_nr, self.sm_put_pulses,
                freq=self.sm_put_freq, set_base=put_pin)
            self.sm_put.irq(self.irq_finished)
        else:
            self.sm_put = None

    @staticmethod
    @rp2.asm_pio(
        in_shiftdir=rp2.PIO.SHIFT_LEFT,
        autopull=False,
        autopush=False,
    )
    def sm_get_pulses():
        set(pindirs, 0)             # set to input
        pull()                      # get start timeout value

# start section: wait for a transition up to start_timeout ticks
        mov(y, pins)                # get the initial pin state
        jmp("start_timeout")

        label("trigger")
        mov(osr, x)                 # save the decremented timeout
        mov(x, pins)                # get the actual pin state
        jmp(x_not_y, "start")       # Transition found

        label("start_timeout")      # test for start timeout
        mov(x, osr)                 # get the timeout value
        jmp(x_dec, "trigger")       # nope, still wait

# trigger seen or timeout
# get the pulse counter, bit_timeout and report the inital state
        label("start")              # got a trigger, go
        pull()                      # pull bit count
        mov(y, osr)                 # store it into the counter
        pull()                      # get the bit timeout value
                                    # keep it in osr
        mov(isr, null)              # clear isr
        in_(pins, 1)                # signal the start level
        push(block)                 # and report it

# pulse loop section, go and time pulses
        jmp(y_dec, "get_pulse")     # Initial decrement & test for zero
        jmp("end")

        label("get_pulse")
        mov(x, osr)                 # preload with the max value
        jmp(pin, "count_high")      # have a high level

        label("count_low")          # timing a low pulse
        jmp(pin, "issue")           #
        jmp(x_dec, "count_low")     # count cycles
        # get's here if the pulse is longer than max_time
        jmp("issue")                # could as well jmp("end")

        label("count_high")
        jmp(pin, "still_high")
        jmp("issue")

        label("still_high")
        jmp(x_dec, "count_high")    # count cycles
        # get's here if the pulse is longer than max_time

        label("issue")              # report the result
        mov(isr, x)
        push(block)
        jmp(y_dec, "get_pulse")     # and go for another loop

        label("end")
        irq(noblock, rel(0))        # get finished!

    @staticmethod
    @rp2.asm_pio(
        set_init=rp2.PIO.OUT_HIGH,
        autopull=False,
    )
    def sm_put_pulses():
        set(pindirs, 1)         # set the Pin to output
        pull()                  # get the number of pulses
        mov(y, osr)
        pull()                  # get start level
        mov(x, osr)
        jmp(x_dec, "hi_pulse")  # start with 1

# create the low pulse
        label("low_pulse")
        jmp(y_dec, "next_low")  # finished?
        jmp("end")              # yes, tell mother

        label("next_low")       # no, the go
        pull()                  # get the duration
        mov(x, osr)
        jmp(x_dec,"set_low")    # Zero length?
        jmp("hi_pulse")         # yes, next pulse

        label("set_low")        # finally go
        set(pins, 0)
        label("low")
        jmp(x_dec, "low")

# create the high pulse
        label("hi_pulse")
        jmp(y_dec, "next_hi")   # finished ?
        jmp("end")              # yes, tell mother

        label("next_hi")        # no, then next check
        pull()                  # get the duration
        mov(x, osr)
        jmp(x_dec, "set_high")  # Is it zero?
        jmp("low_pulse")        # yes, next pulse

        label("set_high")       # no, now Pulse
        set(pins, 1)
        label("high")
        jmp(x_dec, "high")
        jmp("low_pulse")        # now another low pulse

        label("end")
        irq(noblock, rel(0))    # wave finished!

    def irq_finished(self, sm):
        if sm == self.sm_put:  # put irq?
            self.put_done = True
        else:
            self.get_done = True

    def get_pulses(self, buffer, start_timeout=100_000, bit_timeout=100_000):
        if self.sm_get is None:
            raise(ValueError, "get_pulses is not enabled")
        self.get_done = False
        # self.sm_get.restart(self.sm_get_pulses)
        self.sm_get.put(start_timeout)  # set the start timeout
        self.sm_get.put(len(buffer))  # set number of pulses
        self.sm_get.put(bit_timeout)  # set the bit timeout

        self.sm_get.active(1)
        start_state = self.sm_get.get()  # get the start state
        self.sm_get.get(buffer)  # get data
        self.sm_get.active(0)
        buffer[0] = bit_timeout - buffer[0] + 6  # scale the first value
        for i in range(1, len(buffer)):  # scale the other values
            buffer[i] = bit_timeout - buffer[i] + 3
        return start_state

    def put_pulses(self, buffer, start_level=1):
        if self.sm_put is None:
            raise(ValueError, "put_pulses is not enabled")
        self.put_done = False
        print(buffer)
        # compensate handling time
        for i in range(len(buffer)):
            buffer[i] = max(0, buffer[i] - 5)
        # self.sm_put.restart(self.sm_put_pulses)
        self.sm_put.active(1)

        self.sm_put.put(len(buffer))   # tell the size
        self.sm_put.put(start_level != 0) # tell the start level
        self.sm_put.put(buffer)        # send the pulse train
        while self.put_done is False:  # and wait for getting is done
            time.sleep_ms(1)

        self.sm_put.active(0)


#
# Instantiate the class
#

pulses = Pulses(machine.Pin(10, machine.Pin.IN), machine.Pin(11, machine.Pin.OUT), sm_freq=1_000_000)

#
# two test functions
#
def get(samples=10, start_timeout=100_000, bit_timeout=100_000):
    global pulses
    ar = array.array("I", bytearray(samples * 4))
    start = pulses.get_pulses(ar, start_timeout, bit_timeout)
    print("Start state: ", start)
    print(pulses.get_done, ar)

def put(pattern="10 20 30 40", start=1):
    global pulses
    v = [int(i) for i in pattern.strip().split()]
    ar = array.array("H", v)
    pulses.put_pulses(ar, start)
    print(pulses.put_done)

get()
put()
