# Small set of PIO helper functions

This is a small set of helper functions allowing to control the state and report the state of PIO state machines.

## **intitial_pc = sm_restart(sm_nr, program)**

Restarts a state machine. It clears the counters and shift registers and sets the program
counter to the first instructions of the state machine. That is very useful, since then
coding of a state machine does not have to clean up itself all possible lock and error states.
It returns the address of the first instruction.

Parameters:

- **sm_nr** The state machine number in the range of 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.
- **program** The program object which is used in the state machine. This is the name of the state machine function assigned to the state machine.

## **level = sm_rx_fifo_level(sm_nr)**

Returns the number of words in the RX FiFo. The value is 0 if the FiFo is empty.

Parameter:

- **sm_nr** The state machine number in the range of 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.

## **level = sm_tx_fifo_level(sm_nr)**

Returns the number of words in the TX FiFo. The value is 0 if the FiFo is empty. The largest number returned depends on whether the FiFo's of the state machine are joined or not.

Parameter:

- **sm_nr** The state machine number in the range of 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.

## **status = sm_status(sm_nr)**

Returns the status word of the state machine's register FSTAT, as defined in the RP2040 hardware manual, chapter 3.7. It contains the FIFO empty/full flags of all four state machines of a PIO.

Parameter:

- **sm_nr** The state machine number in the range of 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.


## **Example**

This example contains a simple version of a DHT22 driver. It uses `wait()` for the various transitions in the protocol. `wait()` blocks. So this sample driver will end up stuck at the end at label `wait_0` or `wait_1` of the program. Calling `sm_restart()` restart the code again at the `pull()` instruction without the need to delete the state machine and create it again. `sm_rx_fifo_level()` is used to tell, whether data is present, and to be able to abort, if the sensor does not deliver data.

```
from machine import Pin
import rp2
import array
import time
import rp2_util

# the clock is set to 200 kHz or 5µs per tick

@rp2.asm_pio(
    in_shiftdir=rp2.PIO.SHIFT_LEFT,
    set_init=rp2.PIO.OUT_HIGH,
    autopull=False,
    autopush=True,
    push_thresh=8
)
def DHT_pio():
    pull()                      # get the number of clock cycles
    mov(x, osr)                 # for the start pulse
    set(pindirs, 1)             # set to output
    set(pins, 0)

    label("start_pulse")
    jmp(x_dec, "start_pulse")   # test for more wait cycles

    set(pins, 1)        [7]     # and wait seven ticks

    set(pindirs, 0)             # set back to input mode
    wait(1, pin, 0)             # Wait for the 0->1 edge

    label("wait_0")             # wait for the 1->0 edge of 
    wait(0, pin, 0)             # the first or next data bit

    label("wait_1")             # wait for the 0->1 edge
    wait(1, pin, 0)             # of the actual data cycle
nop()               [7]         # wait another 40 µs
    in_(pins, 1)                # get one bit, which is 0 or 1
                                # that will be shifted and pushed
    jmp(pin, "wait_0")          # if it's one, wait for next bit's
                                # falling edge
    jmp("wait_1")               # Otherwise wait for the next bit's
                                # rising egde

pin_base = Pin(10, Pin.OUT, value=1)
sm_freq = 200_000
sm_tick = 1_000_000 // sm_freq  # 5 µs

sm = rp2.StateMachine(0, DHT_pio, freq=sm_freq,
                      set_base=pin_base,
                      in_base=pin_base,
                      jmp_pin=pin_base)

def dht22():

    recv = bytearray(5)
    ipc = rp2_util.sm_restart(0, DHT_pio)
    print("Initial PC =", ipc)
    sm.put(1000 // sm_tick)  # number of wait cycles for the start pulse of 1 ms
    sm.active(1)
    index = 0
    for i in range(1000):
        if rp2_util.sm_rx_fifo_level(0) > 0:
            recv[index] = sm.get()
            index += 1
            if index == len(recv):
                break
        else:
            time.sleep_ms(1)
    else:
        print("Acquistion error")
    sm.active(0)
    print([hex(i) for i in recv])

dht22()
```