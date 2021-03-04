# Class for timing and sending pulses at a GPIO pin.

Trial class to get and put pulse trains on a GPIO pin
using PIO. The pulse duration is set or returned as
the multiple of a basic tick, defined by the PIO clock,
which gives a lot of flexibility. Since the duration values
used can be 32 bit integers, that gives a wide range of
duration and resolution. The maximum frequency for timing
pulses is machine.freq()/2, for sending pulses it's
machine.freq(). So at 125MHz MCU clock
for timing input pulses, the resolution can be 16ns
for a pulse range of ~120ns - ~68 seconds, for sending
the resolution can be 8 ns and the range ~70ns to ~34 seconds.
At lower frequencies for the PIO, resolution and range
scale accordingly.

## 1. Instantiation

pulses = Pulses(get_pin=None, put_pin=None, frequency=1_000_000)

This creates an instance of the Pulses class. Parameters:

- get_pin: A machine.Pin object used for timing pulses at a pin. get_pin should be defined as input pin. If set or left as None, the method for timing pulses is not available.
- put_pin: A machine.Pin object used to send pulses. put_pin should be defined as output pin. If set or left as None, the method for sending pulses is not available.
- frequency: The time tick frequency used to get and put pulses. It must be lower than machine.freq()/2 for get pulses and lower than machine.freq() for put pulses. The basic timing tick is 1/frequency. To avoid problems in calculating an inverse, this parameter is chosen as frequency and not as time unit.

For getting pulses, state machine 0 is used, for putting it's state machine 4. Both state machines are rather large. For getting pulses, its 31 instructions, for sending pulses it's 17. So there is just some room left for other state machines.

## 2. Methods

### 2.1 **get_pulses**

This is the method for timing pulses at a pin. Call and parameters:

start_level = pulses.get_pulses(buffer, start_timeout=100_000, bit_timeout=100_000)

- **buffer** is a bytearray or array of type "B", "H" or "I" which receives the samples values. You can choose the array type based on the maximal value of the pulses which you expect. It must be capable of string the supplied bit_timeout.
- **start_timeout** is the number of ticks get_pulses() waits for the first transition.
- **bit_timeout** is the number of ticks get_pulses() waits for a single bit.
- **start_level** is returned by get_pulses() and tells the level of the first pulse.

When started, get_pulses() waits for up to start_timeout for a transition, and then it will time as many pulses as fit into the buffer. It will always attempt to fill the buffer, even in case of a timeout. So do not set the timeout too large. In case of a timeout, the corresponding bit duration value will be larger than the bit_timeout.

The shortes pulse that can be sampled is 7 ticks for the first pulse and 4 ticks for the remaining ones.

### 2.2 **put_pulses**

This is the method for sending pulses. Call and parameters:

pulses.put_pulses(self, buffer, start_level=1)

- **buffer** must contain the pulse times in multiple of the set tick duration. It can be a bytearray or array of type "B", "H" or "I". The smallest suitable value is 9. If the duration is less than that, it will be skipped, but the level will be considered as changed. So you can use that to extend a pulse duration.

- **start_level** Level of the first pulse. After that, the level will alternate.

## 3. Examples

### 3.1 **Timing pulses**

```
#
# Instantiate the class
#

pulses = Pulses(machine.Pin(10, machine.Pin.IN), machine.Pin(11, machine.Pin.OUT), sm_freq=1_000_000)

def get(samples=10, start_timeout=100_000, bit_timeout=100_000):
global pulses
ar = array.array("I", bytearray(samples * 4))
start = pulses.get_pulses(ar, start_timeout, bit_timeout)
print("Start state: ", start)
print(pulses.get_done, ar)
```

### 3.2 **Sending pulses**

The times are supplied in this example as a tuple.
```
#
# Instantiate the class
#

pulses = Pulses(machine.Pin(10, machine.Pin.IN), machine.Pin(11, machine.Pin.OUT), sm_freq=1_000_000)

def put(pattern=(10, 20, 30, 40,), start=1):
global pulses
ar = array.array("H", pattern)
pulses.put_pulses(ar, start)
print(pulses.put_done)
```

## 4. What next?

- Supporting DMA for data transfer
