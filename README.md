# How it works
## Connection
Using the library pyusb we are able to estabilish a usb connection with the card reader crt 288

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
## Writing
To send commands to the device we need a 64 bytes lenght array , every command needed is contained in the file `Commands_Variable.command_list.py`

```python
crt_288.write(cm.WRITE,command)

#Function used to write and read data from a command

def sendCommand()
```
## Reading
The device always respond to commands sent with an array.array of 64 elements

```python
crt_288.read(cm.READ,64)

#Function used to read more data than a 64 byte package

def recursiveByteGet()
```
# The result
The final objective of this program is to identify a certain type of card that the user is putting inside the card reader editable in the function      def printData(self):

The possible outcome of the card recognitions are :

0. No card inside / Still reading
1. The card is the one requested 
2. The card is spanish but not the one requested
3. The card isn't spanish
4. The card is expired
 
Those values are displayed on the temporary file `/tmp/cardReader.txt`

```python
def writeCardStatus()
```

## Bank names and BIN
To identify the names that we can found on the cards we use a different python script inside the folder `/root/CardReaderAPI/Commands_Variable.py`

It's a function called at the start of the script and for now every monday at 5 am , it returns a list of strings with the name and BIN indentification ( 6 digits number )
### schedule
The library schedule allow use to update this list

```python
import schedule
import Commands_Variable.tablas_BIN as update

def inizializzazione()

  update.bankUpdate()
  schedule.every().monday.at("05:00").do(update.bankUpdate)
```
The schedule library impose the continue usage of the funcion inside the main loop 
```python
schedule.run_pending()
```
## Expired
With this program, we can obtain the expire date of the card ( if needed )

## Card Choosen
In the folder `/root/CardReaderAPI/Commands_Variable/card_accepted.txt` you can write the name of the bank that u want to choose to WRITE **1** on the file `/tmp/cardReader.txt`
 
# Log
With the python library logging we can save the ERRORS and CONSOLE PRINTING if needed
```python

# Custom FileHandler with flush after each log write
class FlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Configure logging with custom handler
log_file = r'./commandline.log'
handler = FlushFileHandler(log_file, mode='a')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[handler, logging.StreamHandler()])

# Redirect stdout and stderr
class StreamToLogger(object):
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

sys.stderr = StreamToLogger(logging.getLogger('STDERR'), logging.ERROR)
#sys.stderr = StreamToLogger(logging.getLogger('STDERR'), logging.INFO)
```
# Extrapulate information from the card
There are 2 ways to obtain the information.

### The method is pretty much the same for both of the modes
After checking that the card is inside the device, the auto-lock mode will activate , securing the card.
To understand if the card has those possibility we use the commands.

  1. For RF -> AUTOTEST_RF_COMMAND 
  2. For IC -> AUTOTEST_IC_COMMAND

**They are builded pretty much the same , with some variation here and there**
Most of the times, the cards will have the RF-ID..
## RF-ID

### 1. RF_ACTIVATE_COMMAND  
Without this command we are not able to communicate with the device.

### 2. RF_COMMAND_VISA / RF_COMMAND_MC
Depends which card are we using , this method will grant us access to a specific memory folder and from there we can continue.

For now we have only VISA and MC, if in the future we will need other types of **AID** we need to access a memory called 1PAY.SYS.DDF01 or 2PAY.SYS.DDF01 to obaid the **AID**.

https://www.eftlab.com/knowledge-base/complete-list-of-application-identifiers-aid
### 3. RF_PDOL / def BuildingPDOL 
° What is the PDOL? Processing Options Data Object List , needed by the card in processing the GET PROCESSING OPTIONS.
° Sometimes is not needed a custom on, so we sent the standard command RF_PDOL.
° With the response of this command, we can extrapolate the position of the RECORDS in the memory. **AFL**

The data inside this response is **ugly**, here u can find **AIP** and **AFL** , sometimes even the **CARD NUMBER**, every **AFL** record needs 4 bytes.
After putting those values inside a list we can pass them on the next function to read from a certain record.

### 4. RF_ASK_BINARY -> def readRecords()
The response of the PDOL can get us a list of the records avaliable, the next thing to do is to search for specific 1/2 bytes correlated to the user card number and expired date needed.

We need to build the `RF_ASK_BINARY` withe the **AFL** that we got.

We don't know exactly where the data that we need is allocated.

### 5. def analyzeSFI()
This function will read the response of the **RECORDS** asked found any math with the data we need.

### 8. def printData()
Used for checking if the card is expired

### 9. def checkValidity()
If we have found the card BIN ( 6 numbers ) we can compare it to the database that we have

### 10. def writeCardStatus()
Create and modify the values inside based on the previous reasons ( Not Spanish, Expired , etc.. ) , when the program will restart the card will write 0 and it won't change it's values until another card will be put inside



# Other functions inside
## def cleanup()
Used for restoring the file `/tmp/cardReader.txt`, the function will be called at the end of the program ( Forced end / Problems )
```python
import atexit

def cleanup():
    writeCardStatus("0")

atexit.register(cleanup)
```
## def printByteString()
Used for printing the response of the device in **HEX** and not **INT**
```python
def printByteString(response):

    a = ">>> ["

    for b in response:
        a+= " "
        a+=('%x'% b)

    a+="]"
    print(a)
```
## def cardIsInside()
Used for checking if the card is **inside** or **not** and the device is  **locked** or **not**.
The [6] value is the **Lock** value, the [7] if the card is **Inside**
```python
def cardIsInside():

    response = sendCommand(cm.ICRW_COMMAND)

    if response[6] == 0x30 and response[7] == 0x32 : print("Inizializzazione");return True

    elif response[7] == 0x32 and response[6] == 0x31 : print("Rimuovere la carta");return False

    else : print("Inserire carta");return False
```
## def has_RF()
Used to check if the device is able to communicate with RF-ID, it will also contain the **name** of RF-ID
```python
def has_RF():

    response = sendCommand(cm.AUTOTEST_RF_COMMAND)

    if len(response) == 0  : print("RF-ID non presente");return False,"Don't have RF-ID"
    elif response == cm.NULL : print("Disconnected while reading checking RF-ID");return False,"Don't have RF-ID"
    else : print("RF-ID presente");return True,cm.RF_CARD_TYPE.get(response[8])
```
## def has_IC()
Used to check if the device is able to communicate with the CHIP, it will also contain the **name** of CHIP
```python
def has_IC():

    response = sendCommand(cm.AUTOTEST_IC_COMMAND)

    if len(response) == 0 : print("IC-CHIP non presente");return False,"Don't have CHIP"
    elif response == cm.NULL : print("Disconnected while reading checking chip");return False,"Don't have CHIP"
    else : print("IC-CHIP presente");name = cm.IC_CARD_TYPE.get(response[8]).get(response[9]);return True,name
```
## def bcc()
Used to create the final **CheckSum** (BCC) it returns a **byte**
```python
def bcc(self,byteBCC):

    result = 0x00

    for i in range(len(byteBCC)):

        result ^= byteBCC[i]


        if byteBCC[i] == 0x00:

            if byteBCC[i+1] == 0x03:

                result ^= byteBCC[i+1] 
                break

    return result
```
## def getDataFromPDOL()
Used only for the purpose of storing the **Card Number** if we can found it while getting the **AIP** and **AFL**
```python
def getDataFromPDOL(self,response):

    lenghtT2 = response[0]

    hex_string  = ''.join(format(response[i+1],'02x')for i in range(lenghtT2))

    hex_string = hex_string.split("d",maxsplit=1)

    self.cardNumber = hex_string[0].replace(" ","")

    self.cardExpiredDate = hex_string[1][0:2]+" "+hex_string[1][2:4]
```
## def checkCardDate()
Used to check if the Card is still **Valid** or **Not**, the storing inside the Class variable
```python
def checkCardDate(self):

    

    if len(self.cardExpiredDate) == 5 : self.cardExpiredDate = (self.cardExpiredDate+"-31").replace(" ","-")

    else : self.cardExpiredDate = self.cardExpiredDate.replace(" ","-")[:-1]
    
    print(self.cardExpiredDate)

    print("Year-month-day")

    date = datetime.strptime(self.cardExpiredDate,'%y-%m-%d').date()

    if date <= datetime.today().date() : print("CARTA SCADUTA");self.cardValidity = False

    else : print("CARTA ANCORA VALIDA");self.cardValidity = True
```


### More..
1. This spaghetti noodles code isn't my best work, hope you will not get any bugs or errors xoxo
2. For some reason after changing the python library ( cuz the kernel of the machine doesn't support hid ) the writing and response became more slow.
3. In the future you can cut some corners to make it faster **SURELY**
### Useful Links
1. If u need to know what certain `tags` means or entire `tvl` codes : https://emvlab.org/main/
2. Here's a list of the various `codes` that the card can recieve : https://gist.github.com/hemantvallabh/d24d71a933e7319727cd3daa50ad9f2c
3. Here's a list of the various `response` that u can recieve from the reader : https://www.eftlab.com/knowledge-base/complete-list-of-apdu-responses
4. Tools for engineers working in the Payment Card Industry : https://paymentcardtools.com/
