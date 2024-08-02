# How it works

using the library pyusb we are able to estabilish a usb connection with the card reader crt 288

```python
import usb

VENDOR_ID = 0x23D8
PRODUCT_ID = 0x0285

crt_288 = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

#If there are drivers pre-installed inside in the kernel, we need to detach them

crt_288.detach_kernel_driver(0)

#Ready the device

crt_288.set_configuration()



#Function used to estabilish the connection with the device or reconnection

def connect()
```

to send commands to the device we need a 64 bytes lenght array , every command needed is contained in the file Commands_Variable.command_list.py

```python
crt_288.write(cm.WRITE,command)

#Function used to write and read data from a command

def sendCommand()
```

the device always respond to commands sent with an array.array of 64 elements

```python
crt_288.read(cm.READ,64)

#Function used to read more data than a 64 byte package

def recursiveByteGet()
```
