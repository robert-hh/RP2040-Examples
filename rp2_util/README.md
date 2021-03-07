# Small set of PIO and DMA for PIO and UART helper functions

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

Returns the status word of the state machine's register FSTAT, as defined in the RP2040 hardware manual, chapter 3.7. It contains the FIFO empty/full flags of the requested state machine. 

Parameter:

- **sm_nr** The state machine number in the range of 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.

The below listed symbols are provided for the flag values, which can be used to mask the results (see the example below):

SM_FIFO_RXFULL  
SM_FIFO_RXEMPTY   
SM_FIFO_TXFULL   
SM_FIFO_TXEMPTY   

## ** ctrl = sm_dma_get(chan, sm_nr, data, nword)**

Set up the DMA to transfer words from the state machine to memory.

Parameters:

- **chan** The number of the DMA channel. Suitable values ar 0-11
- **sm_nr** The number of the state machine. Suitable values are 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.
- **data** The data buffer into which the data is to be transferred. The type is bytearray or array of type "B", "H" or "I" which receives the samples values. The data type must match the push_thresh set in the state machine, because the transfer size of the DMA is taken from that setting. **So even if the state machine is defined with auto_push=False, the push_thresh must be declared.**
- **nword** The number of data items to be transferred.

The return value is the control word set in the DMA CTRL register and only interesting for debug purposes.

For telling when the transfer is finished, either a IRQ raised by the state machine can be used, or reading the number of the remaining transfer count with rp2_util.dma_transfer_count() (see below.), which gets 0 when the transfer is finished. To stop a transfer use rp2_util.dma_abort().

## ** ctrl = sm_dma_put(chan, sm_nr, data, nword)**

Set up the DMA to transfer words from memory to the state machine.

Parameters:

- **chan** The number of the DMA channel. Suitable values ar 0-11
- **sm_nr** The number of the state machine. Suitable values are 0-7. State machines 0-3 are assigned to PIO0,
state machines 4-7 are assigned to PIO1. This is a number, not the state machine object.
- **data** The data buffer from which the data is to be transferred. The type is bytearray or array of type "B", "H" or "I" which receives the samples values. The data type must match the pull_thresh set in the state machine, because the transfer size of the DMA is taken from that setting. **So even if the state machine is defined with auto_pull=False, the pull_thresh must be declared.** Note that for transfer sizes < 32 bit the TXFIFO register will be partially filled only, and the remainder of the register is undefined. So only out() instructions up to that size will shift out valid data. A mov(x, osr) instruction for instance after a pull() will set x to a partially undefined value. If you want to copy the lower N bits to x, use out(x, N), which fill up the remainder of x with 0.
- **nword** The number of data items to be transferred.

The return value is the control word set in the DMA CTRL register and only interesting for debug purposes.

For telling when the transfer is finished, either a IRQ raised by the state machine can be used, or reading the number of the remaining transfer count with rp2_util.dma_transfer_count() (see below.), which gets 0 when the transfer is finished. To stop a transfer use rp2_util.dma_abort().

## ** ctrl = uart_dma_read(chan, uart_nr, data, nword)

Set up the DMA to transfer words from a UART to memory.

Parameters:

- **chan** The number of the DMA channel. Suitable values ar 0-11
- **uart_nr** The number of the UART. Suitable values are 0 and 1. This is a number, not the UART object.
- **data** The data to which the data is to be transferred. The type is bytearray or array of type "B"
- **nword** The number of data items to be transferred.

The return value is the control word set in the DMA CTRL register and only interesting for debug purposes.

For telling when the transfer is finished, either a IRQ raised by the state machine can be used, or reading the number of the remaining transfer count with rp2_util.dma_transfer_count() (see below.), which gets 0 when the transfer is finished. To stop a transfer use rp2_util.dma_abort().

## ** dma_abort(chan)**

Aborts the current transfer. That may be as well an unfinished previous transfer, and therefore a valid measure to start with a known state.

## ** count = dma_transfer_count(chan)**

Returns the number of the **remaining** items to be transferred. When the transfer is finished, the value is 0.

## ** count = dma_write_address(chan)**

Returns the address where the **next** transferred items will be written to.

## ** count = dma_read_address(chan)**

Returns the address where the **next** transferred items will be read from.

## **Example**

### DHT22 driver
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
sm_nr = 0

sm = rp2.StateMachine(sm_nr, DHT_pio, freq=sm_freq,
                      set_base=pin_base,
                      in_base=pin_base,
                      jmp_pin=pin_base)

def dht22():

    recv = bytearray(5)
    ipc = rp2_util.sm_restart(sm_nr, DHT_pio)
    print("Initial PC =", ipc)
    sm.put(1000 // sm_tick)  # number of wait cycles for the start pulse of 1 ms
    sm.active(1)
    index = 0
    for i in range(1000):
        if rp2_util.sm_rx_fifo_level(sm_nr) > 0:
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

### Getting data from the state machine using DMA

This is just the lower part of the previous example. The state machine itself is not changed.
```
pin_base = Pin(10, Pin.OUT, value=1)
sm_freq = 200_000
sm_tick = 1_000_000 // sm_freq
sm_nr = 5
dma_chan = 0

sm = rp2.StateMachine(sm_nr, DHT_pio, freq=sm_freq,
                        set_base=pin_base, in_base=pin_base,
                        jmp_pin=pin_base)

def dht22():
    recv = bytearray(5)

    print(rp2_util.sm_restart(sm_nr, DHT_pio))
    sm.put(1000 // sm_tick)  # number of wait cycles for the start pulse
    sm.active(1)
    rp2_util.sm_dma_get(dma_chan, sm_nr, recv, len(recv))
    for i in range(1000):
        if rp2_util.sm_dma_count(dma_chan) == 0:
            break
        else:
            time.sleep_ms(1)
    else:
        print("Acquistion error")
    sm.active(0)
    print([hex(i) for i in recv])

dht22()
```

### Reading the status of a state machine  

Assuming a state machine sm has been defined with the number sm_nr.

```
import rp2
import rp2_util

status = rp2_util.sm_status(sm_nr)
if status & SM_FIFO_TXEMPTY:
    sm.put(value)
else:
    pass
```

### Read data from UART using DMA

```
from machine import UART, Pin
import rp2_util
import time

UART_NR = 0
DMA_CHAN = 0

uart = UART(UART_NR, 460800, tx=Pin(12), rx=Pin(13))
rp2_util.dma_abort(DMA_CHAN)  # start with known state

data = bytearray(1024)
read_size = len(data)

while True:
    rp2_util.uart_dma_read(DMA_CHAN, UART_NR, data, read_size)
    while True:
        received = read_size - rp2_util.dma_transfer_count(DMA_CHAN)
        if received > 200:
            break
        else:
            print(received)
            time.sleep_ms(500)
    rp2_util.dma_abort(DMA_CHAN)  # abort the current transfer
    print(received, data[:received])
```