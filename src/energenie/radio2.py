# radio2.py  15/04/2015  D.J.Whale
#
# New version of the radio driver, with most of the fast stuff pushed into C.
#
# NOTE 1: This is only used for OOK transmit & FSK transmit at the moment.
# FSK receive is currently being re-implemented in radio.c

# NOTE 2: Also there is an idea to do a python wrapper, build the C code
# for an Arduino and wrap it with a simple serial message handler.
# This would then make it possible to use the Energenie Radio on a Mac/PC/Linux
# machine but by still using the same higher level Python code.
# All you would need is a different radio.py that marshalled data to and from
# the Arduino via pyserial.

#TODO: Should really add parameter validation here, so that C code doesn't have to.
#although it will be faster in C (C could be made optional, like an assert?)

##LIBNAME = "drv/radio_rpi.so"
LIBNAME = "drv/radio_mac.so" # testing

import time
import ctypes
from os import path
mydir = path.dirname(path.abspath(__file__))

libradio                     = ctypes.cdll.LoadLibrary(mydir + "/" + LIBNAME)
radio_init_fn                = libradio["radio_init"]
radio_reset_fn               = libradio["radio_reset"]
radio_get_ver_fn             = libradio["radio_get_ver"]
radio_modulation_fn          = libradio["radio_modulation"]
radio_transmitter_fn         = libradio["radio_transmitter"]
radio_transmit_fn            = libradio["radio_transmit"]
radio_send_payload_fn        = libradio["radio_send_payload"]
radio_receiver_fn            = libradio["radio_receiver"]
radio_is_receive_waiting_fn  = libradio["radio_is_receive_waiting"]
radio_get_payload_fn         = libradio["radio_get_payload"]
radio_standby_fn             = libradio["radio_standby"]
radio_finished_fn            = libradio["radio_finished"]

RADIO_MODULATION_OOK = 0
RADIO_MODULATION_FSK = 1

# A temporary limit, the receiver will only receive 1 FIFO worth of data maximul
# This includes the length byte at the start of an OpenThings message
MAX_RX_SIZE = 66


#TODO RADIO_RESULT_XX

def unimplemented(m):
    print("warning: method is not implemented:%s" % m)
    return m


def deprecated(m):
    """Load-time warning about deprecated method"""
    print("warning: method is deprecated:%s" % m)
    return m


def untested(m):
    """Load-time warning about untested function"""
    print("warning: method is untested:%s" % m)
    return m


def disabled(m):
    """Load-time waring about disabled function"""
    print("warning: method is disabled:%s" % m)
    def nothing(*args, **kwargs):pass
    return nothing


def init():
    """Initialise the module ready for use"""
    #extern void radio_init(void);
    radio_init_fn()


def reset():
    """Reset the radio device"""
    #extern void radio_reset(void);
    radio_reset_fn()


def get_ver():
    """Read out the version number of the radio"""
    return radio_get_ver_fn()


def modulation(fsk=None, ook=None):
    """Switch modulation, if needed"""
    #extern void radio_modulation(RADIO_MODULATION mod);
    if ook:
        m = ctypes.c_int(RADIO_MODULATION_OOK)
    elif fsk:
        m = ctypes.c_int(RADIO_MODULATION_FSK)
    else:
        raise RuntimeError("Must choose fsk or ook mode")
    radio_modulation_fn(m)


def transmitter(fsk=None, ook=None):
    """Change into transmitter mode"""
    #extern void radio_transmitter(RADIO_MODULATION mod);
    if ook:
        m = ctypes.c_int(RADIO_MODULATION_OOK)
    elif fsk:
        m = ctypes.c_int(RADIO_MODULATION_FSK)
    else: # defaults to FSK
        m = ctypes.c_int(RADIO_MODULATION_FSK)
    radio_transmitter_fn(m)


def transmit(payload, outer_times=1, inner_times=8, outer_delay=0):
    """Transmit a single payload using the present modulation scheme"""
    #Note, this optionally does a mode change before and after
    #extern void radio_transmit(uint8_t* payload, uint8_t len, uint8_t repeats);

    framelen = len(payload)
    if framelen < 1 or framelen > 255:
        raise ValueError("frame len must be 1..255")
    if outer_times < 1:
        raise ValueError("outer_times must be >0")
    if inner_times < 1 or inner_times > 255:
        raise ValueError("tx times must be 0..255")

    framelen     = len(payload)
    Frame        = ctypes.c_ubyte * framelen
    txframe      = Frame(*payload)
    inner_times  = ctypes.c_ubyte(inner_times)
    
    for i in range(outer_times):
        radio_transmit_fn(txframe, framelen, inner_times)
        if outer_delay != 0:
            time.sleep(outer_delay)


def send_payload(payload, outer_times=1, inner_times=8, outer_delay=0):
    """Transmit a payload in present modulation scheme, repeated"""
    #Note, this does not do a mode change before or after,
    #and assumes the mode is already transmit
    #extern void radio_send_payload(uint8_t* payload, uint8_t len, uint8_t times);

    framelen = len(payload)
    if framelen < 1 or framelen > 255:
        raise ValueError("frame len must be 1..255")
    if outer_times < 1:
        raise ValueError("outer_times must be >0")
    if inner_times < 1 or inner_times > 255:
        raise ValueError("tx times must be 0..255")
    Frame          = ctypes.c_ubyte * framelen
    txframe        = Frame(*payload)
    inner_times    = ctypes.c_ubyte(inner_times)

    for i in range(outer_times):
        radio_send_payload_fn(txframe, framelen, inner_times)
        if outer_delay != 0:
            time.sleep(outer_delay)


@untested
def receiver(fsk=None, ook=None):
    """Change into receiver mode"""
    #extern void radio_receiver(RADIO_MODULATION mod);
    if ook:
        m = ctypes.c_int(RADIO_MODULATION_OOK)
    elif fsk:
        m = ctypes.c_int(RADIO_MODULATION_FSK)
    else: # defaults to FSK
        m = ctypes.c_int(RADIO_MODULATION_FSK)

    radio_receiver_fn(m)


@untested
def is_receive_waiting():
    """Check to see if a payload is waiting in the receive buffer"""
    #extern RADIO_RESULT radio_is_receive_waiting(void);
    res = radio_is_receive_waiting_fn()
    # this is RADIO_RESULT_OK_TRUE or RADIO_RESULT_OK_FALSE
    # so it is safe to evaluate it as a boolean number.
    return (res != 0)


@untested
def receive(size=None):
    """Receive a single payload"""
    #NOTE for OOK, need to put in expected size of 16 bytes (includes preamble)

    if size == None: # count byte preceeded
        size = MAX_RX_SIZE
        rxsize = ctypes.byref(size)

    else: # fixed size receive
        rxsize = ctypes.c_ubyte(None)

    Buffer = ctypes.c_ubyte * size
    rxbuf  = Buffer()
    buflen = ctypes.c_ubyte(size)

    #RADIO_RESULT radio_get_payload(uint8_t* buf, uint8_t buflen, uint8_t* rxlen)

    result = radio_get_payload_fn(rxbuf, buflen, rxsize)
    if result != 0: # RADIO_RESULT_OK
        raise RuntimeError("Receive failed, error code %d" % result)

    # turn buffer into a list of bytes, using 'size' as the counter
    rxlist = []
    for i in range(size):
        rxlist.append(rxbuf[i])

    return rxlist # Python len(rxlist) tells us how many bytes including length byte if present


def standby():
    """Put radio into standby mode"""
    #extern void radio_standby(void);
    radio_standby_fn()


def finished():
    """Close the library down cleanly when finished"""
    #extern void radio_finished(void);
    radio_finished_fn()


#----- TEMPORARILY EXPOSE EMBEDDED SPI MODULE ---------------------------------

# Temporarily expose the embedded spi/gpio interface.
# This is to allow older version of code to share the .so
# rather than us having to maintain both spi.so and radio_rpi.so
#
# This is a stepping stone towards a single unified radio_rpi.so
# that does both OOK and FSK physical layer.

spi_init_defaults_fn = libradio["spi_init_defaults"]
spi_init_fn          = libradio["spi_init"]
spi_select_fn        = libradio["spi_select"]
spi_deselect_fn      = libradio["spi_deselect"]
spi_byte_fn          = libradio["spi_byte"]
spi_frame_fn         = libradio["spi_frame"]
spi_finished_fn      = libradio["spi_finished"]

#gpio_init_fn         = libradio["gpio_init"]
#gpio_setin_fn        = libradio["gpio_setin"]
gpio_setout_fn       = libradio["gpio_setout"]
gpio_high_fn         = libradio["gpio_high"]
gpio_low_fn          = libradio["gpio_low"]
#gpio_write_fn        = libradio["gpio_write"]
#gpio_read_fn         = libradio["gpio_read"]

RESET     = 25 # BCM GPIO
LED_GREEN = 27 # BCM GPIO (not B rev1)
LED_RED   = 22 # BCM GPIO


@disabled
def spi_trace(msg):
    print(str(msg))


@deprecated
def spi_reset():
    spi_trace("reset")

    reset = ctypes.c_int(RESET)
    gpio_setout_fn(reset)
    gpio_high_fn(reset)
    time.sleep(0.1)
    gpio_low_fn(reset)
    time.sleep(0.1)

    # Put LEDs into known off state
    led_red = ctypes.c_int(LED_RED)
    led_green = ctypes.c_int(LED_GREEN)
    gpio_setout_fn(led_red)
    gpio_low_fn(led_red)
    gpio_setout_fn(led_green)
    gpio_low_fn(led_green)

@deprecated
def spi_init_defaults():
    spi_trace("calling init_defaults")
    spi_init_defaults_fn()


@deprecated
def spi_init():
    spi_trace("calling init")
    #TODO build a config structure
    #TODO pass in pointer to config structure
    #spi_init_fn()


@deprecated
def spi_start_transaction():
    """Start a transmit or receive, perhaps multiple bursts"""
    # turn the GREEN LED on
    led_green = ctypes.c_int(LED_GREEN)
    gpio_high_fn(led_green)


@deprecated
def spi_end_transaction():
    """End a transmit or receive, perhaps multiple listens"""
    # turn the GREEN LED off
    led_green = ctypes.c_int(LED_GREEN)
    gpio_low_fn(led_green)


@deprecated
def spi_select():
    spi_trace("calling select")
    spi_select_fn()


@deprecated
def spi_deselect():
    spi_trace("calling deselect")
    spi_deselect_fn()


@deprecated
def spi_byte(tx):
    txbyte = ctypes.c_ubyte(tx)
    #spi_trace("calling byte")
    rxbyte = spi_byte_fn(txbyte)
    return rxbyte


@deprecated
def spi_frame(txlist):
    spi_trace("calling frame ")
    framelen = len(txlist)
    #spi_trace("len:" + str(framelen))
    Frame = ctypes.c_ubyte * framelen
    txframe = Frame(*txlist)
    rxframe = Frame()

    spi_frame_fn(ctypes.byref(txframe), ctypes.byref(rxframe), framelen)
    rxlist = []
    for i in range(framelen):
        rxlist.append(rxframe[i])
    return rxlist


@deprecated
def spi_finished():
    spi_trace("calling finished")
    spi_finished_fn()

# END
