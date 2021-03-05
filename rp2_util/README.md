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

