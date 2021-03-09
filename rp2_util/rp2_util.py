#
# set set of small functions supporting the use of the PIO
#

PIO0_BASE = const(0x50200000)
PIO1_BASE = const(0x50300000)

# register indices into the array of 32 bit registers
PIO_CTRL = const(0)
PIO_FSTAT = const(1)
PIO_FLEVEL = const(3)
SM_REG_BASE = const(0x32)  # start of the SM state tables
# register offsets into the per-SM state table
SMx_CLKDIV = const(0)
SMx_EXECCTRL = const(1)
SMx_SHIFTCTRL = const(2)
SMx_ADDR = const(3)
SMx_INSTR = const(4)
SMx_PINCTRL = const(5)

SMx_SIZE = const(6)  # SM state table size

SM_FIFO_RXFULL  = const(0x00000001)
SM_FIFO_RXEMPTY = const(0x00000100)
SM_FIFO_TXFULL  = const(0x00010000)
SM_FIFO_TXEMPTY = const(0x01000000)


@micropython.viper
def sm_restart(sm: int, program) -> uint:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
        initial_pc = uint(program[1])
    else:  # PIO1
        pio = ptr32(uint(PIO1_BASE))
        initial_pc = uint(program[2])
    sm %= 4
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_INSTR
    pio[PIO_CTRL] = 1 << (sm + 4)  # reset the registers
    # now execute a jmp instruction to the initial PC
    # Since the code for the unconditional jump is
    # 0 + binary address, this is effectively the address
    # to be written in the INSTR register.
    pio[smx] = initial_pc  # set the actual PC to the start adress
    return initial_pc

@micropython.viper
def sm_rx_fifo_level(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    else:  # PIO1
        pio = ptr32(uint(PIO1_BASE))
    sm %= 4
    return (pio[PIO_FLEVEL] >> (8 * sm + 4)) & 0x0f

@micropython.viper
def sm_tx_fifo_level(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    else:  # PIO1
        pio = ptr32(uint(PIO1_BASE))
    sm %= 4
    return (pio[PIO_FLEVEL] >> (8 * sm)) & 0x0f

@micropython.viper
def sm_fifo_status(sm: int) -> int:
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    else:  # PIO1
        pio = ptr32(uint(PIO1_BASE))
    sm %= 4
    return (pio[PIO_FSTAT] >> sm) & 0x01010101

@micropython.viper
def sm_fifo_join(sm: int, action: int):
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
    else:  # PIO1
        pio = ptr32(uint(PIO1_BASE))
    sm %= 4
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_SHIFTCTRL

    if action == 0:  # disable join
        pio[smx] = ((pio[smx] >> 16) & 0x3fff) << 16
    elif action == 1:  # join RX
        pio[smx] = (((pio[smx] >> 16) & 0x3fff) | (1 << 15)) << 16
    elif action == 2:  # join TX
        pio[smx] = (((pio[smx] >> 16) & 0x3fff) | (1 << 14)) << 16

#
# PIO register byte address offsets
#
PIO_TXF0 = const(0x10)
PIO_TXF1 = const(0x14)
PIO_TXF2 = const(0x18)
PIO_TXF3 = const(0x1c)
PIO_RXF0 = const(0x20)
PIO_RXF1 = const(0x24)
PIO_RXF2 = const(0x28)
PIO_RXF3 = const(0x2c)

#
# DMA registers
#
DMA_BASE = const(0x50000000)
# Register indices into the DMA register table
READ_ADDR = const(0)
WRITE_ADDR = const(1)
TRANS_COUNT = const(2)
CTRL_TRIG = const(3)
CTRL_ALIAS = const(4)
TRANS_COUNT_ALIAS = const(9)
CHAN_ABORT = const(0x111)  # Address offset / 4
BUSY = const(1 << 24)
#
# Template for assembling the DMA control word
#
IRQ_QUIET = const(1)  # do not generate an interrupt
CHAIN_TO = const(0)  # do not chain
RING_SEL = const(0)
RING_SIZE = const(0)  # no wrapping
HIGH_PRIORITY = const(1)
EN = const(1)
#
# Read from the State machine using DMA:
# DMA channel, State machine number, buffer, buffer length
#
@micropython.viper
def sm_dma_get(chan:int, sm:int, dst:ptr32, nword:int) -> int:

    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
        TREQ_SEL = sm + 4  # range 4-7
    else:  # PIO1
        sm %= 4
        pio = ptr32(int(PIO1_BASE))
        TREQ_SEL = sm + 12  # range 12 - 13
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_SHIFTCTRL  # get the push threshold
    DATA_SIZE = (pio[smx] >> 20) & 0x1f  # to determine the transfer size
    smx = DATA_SIZE
    if DATA_SIZE > 16 or DATA_SIZE == 0:
        DATA_SIZE = 2  # 32 bit transfer
    elif DATA_SIZE > 8:
        DATA_SIZE = 1  # 16 bit transfer
    else:
        DATA_SIZE = 0  # 8 bit transfer

    INCR_WRITE = 1  # 1 for increment while writing
    INCR_READ = 0  # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 6) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                        (HIGH_PRIORITY << 1) | (EN << 0))
    dma[READ_ADDR] = uint(pio) + PIO_RXF0 + sm * 4
    dma[WRITE_ADDR] = uint(dst)
    dma[TRANS_COUNT] = nword
    dma[CTRL_TRIG] = DMA_control_word  # and this starts the transfer
    return DMA_control_word

#
# Write to the State machine using DMA:
# DMA channel, State machine number, buffer, buffer length
#
@micropython.viper
def sm_dma_put(chan:int, sm:int, src:ptr32, nword:int) -> int:

    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    if sm < 4:   # PIO 0
        pio = ptr32(uint(PIO0_BASE))
        TREQ_SEL = sm  # range 0-3
    else:  # PIO1
        sm %= 4
        pio = ptr32(uint(PIO1_BASE))
        TREQ_SEL = sm + 8  # range 8-11
    smx = SM_REG_BASE + sm * SMx_SIZE + SMx_SHIFTCTRL  # get the pull threshold
    DATA_SIZE = (pio[smx] >> 25) & 0x1f  # to determine the transfer size
    if DATA_SIZE > 16 or DATA_SIZE == 0:
        DATA_SIZE = 2  # 32 bit transfer
    elif DATA_SIZE > 8:
        DATA_SIZE = 1  # 16 bit transfer
    else:
        DATA_SIZE = 0  # 8 bit transfer

    INCR_WRITE = 0  # 1 for increment while writing
    INCR_READ = 1  # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 9) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                        (HIGH_PRIORITY << 1) | (EN << 0))
    dma[READ_ADDR] = uint(src)
    dma[WRITE_ADDR] = uint(pio) + PIO_TXF0 + sm * 4
    dma[TRANS_COUNT] = nword
    dma[CTRL_TRIG] = DMA_control_word  # and this starts the transfer
    return DMA_control_word

#
# UART registers
#
UART0_BASE = const(0x40034000)
UART1_BASE = const(0x40038000)

#
# Read from UART using DMA:
# DMA channel, UART number, buffer, buffer length
#
@micropython.viper
def uart_dma_read(chan:int, uart_nr:int, data:ptr32, nword:int) -> int:

    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    if uart_nr == 0:   # UART0
        uart_dr = uint(UART0_BASE)
        TREQ_SEL = 21
    else:  # UART1
        uart_dr = uint(UART1_BASE)
        TREQ_SEL = 23
    DATA_SIZE = 0  # byte transfer
    INCR_WRITE = 1  # 1 for increment while writing
    INCR_READ = 0  # 0 for no increment while reading
    DMA_control_word = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                        (RING_SIZE << 9) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                        (HIGH_PRIORITY << 1) | (EN << 0))
    dma[READ_ADDR] = uart_dr
    dma[WRITE_ADDR] = uint(data)
    dma[TRANS_COUNT] = nword
    dma[CTRL_TRIG] = DMA_control_word  # and this starts the transfer
    return DMA_control_word
#
# Get the current transfer count
#
@micropython.viper
def dma_transfer_count(chan:uint) -> int:
    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    return dma[TRANS_COUNT]
#
# Get the current write register value
#
@micropython.viper
def dma_write_addr(chan:uint) -> int:
    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    return dma[WRITE_ADDR]

#
# Get the current read register value
#
@micropython.viper
def dma_read_addr(chan:uint) -> int:
    dma=ptr32(uint(DMA_BASE) + chan * 0x40)
    return dma[READ_ADDR]
#
# Abort an transfer
#
@micropython.viper
def dma_abort(chan:uint):
    dma=ptr32(uint(DMA_BASE))
    dma[CHAN_ABORT] = 1 << chan
    while dma[CHAN_ABORT]:
        time.sleep_us(10)
