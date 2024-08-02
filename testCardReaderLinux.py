import usb

import atexit

import sys

import logging

import logging.handlers

import time

from datetime import datetime

import Commands_Variable.command_list as cm

import schedule

import Commands_Variable.tablas_BIN as update

VENDOR_ID = 0x23D8
PRODUCT_ID = 0x0285

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


#Check del dispositivon se presente
crt_288 = None



# Continua a leggere i valori inviati dallo scanner , in caso di nessun valore [] lista vuota e si interrompe

def recursiveByteGet(response:bytes):

    while True:
        try :
            new_risponse = crt_288.read(cm.READ,64).tobytes()
        except usb.USBError:
            new_risponse = []
        if len(new_risponse) != 0:

            response+=new_risponse #prima era... for i in new_risponse : response+=i.to_bytes(1,'big')

        else : break

    return response





# Invio comando + handshake finale


def sendCommand(command):

    time.sleep(0.2)
    try :
        crt_288.write(cm.WRITE,command,)
    except usb.USBError:
        print("Device disconnected while writing COMMAND")
        connect()

    print("------->  "+ cm.constants.get(command) if command in cm.constants else "PDOL / GET RECORDS")

    try :
        response = crt_288.read(cm.READ,64,timeout=1000).tobytes()
    except usb.USBError:
        print("Device  disconnected while READING or timeout error")
        connect()
        response = []

    if len(response) != 0:

        if response[0] == cm.HANDSHAKE_CODE : response = b'' ; response = recursiveByteGet(response)

        elif response[0] == cm.NAK : print("ERRORE----BCC ERRATO SOLITAMENTE")

        elif response[0] == cm.RECIEVE : response = recursiveByteGet(response)
    else:
        return cm.NULL
    
    time.sleep(0.1)

    try :
        crt_288.write(cm.WRITE,cm.HANDSHAKE_COMMAND)
    except usb.USBError:
        print("Device disconnected while writing HANDSHAKE")
        connect()
        response = cm.NULL

    return response


def connect():
    global crt_288
    crt_288 = None
    time.sleep(2)
    while True:
        crt_288 = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if crt_288 != None:
            crt_288.reset()
            print("Device found")
            break
        else:
            print("Device not connected") 
        time.sleep(2)

    if crt_288.is_kernel_driver_active(0):
        crt_288.detach_kernel_driver(0)
    crt_288.set_configuration()
    time.sleep(5)
    return crt_288


connect() 

 
def writeCardStatus(status:str):
    with open('/tmp/cardReader.txt','w') as cr:
        cr.write(status)
        cr.close()

def cleanup():
    writeCardStatus("0")

atexit.register(cleanup)
# Update bank + comando automatico di blocco

def inizializzazione():
    # Per controlli veloci, commentare la funzione sottostante

    update.bankUpdate()

    schedule.every().monday.at("05:00").do(update.bankUpdate)

    sendCommand(cm.AUTO_LOCK_ON_COMMAND)

    sendCommand(cm.OPEN_COMMAND)



# Permette di stampare una serie di byte

def printByteString(response):

    a = ">>> ["

    for b in response:
        a+= " "
        a+=('%x'% b)

    a+="]"
    print(a)




# Stampa in che stato si trova la carta

def cardIsInside():

    response = sendCommand(cm.ICRW_COMMAND)

    if response[6] == 0x30 and response[7] == 0x32 : print("Inizializzazione");return True

    elif response[7] == 0x32 and response[6] == 0x31 : print("Rimuovere la carta");return False

    else : print("Inserire carta");return False



# Possiede RF-ID , NOME

def has_RF():

    response = sendCommand(cm.AUTOTEST_RF_COMMAND)

    if len(response) == 0  : print("RF-ID non presente");return False,"Don't have RF-ID"
    elif response == cm.NULL : print("Disconnected while reading checking RF-ID");return False,"Don't have RF-ID"
    else : print("RF-ID presente");return True,cm.RF_CARD_TYPE.get(response[8])



# Possiede IC , NOME    

def has_IC():

    response = sendCommand(cm.AUTOTEST_IC_COMMAND)

    if len(response) == 0 : print("IC-CHIP non presente");return False,"Don't have CHIP"
    elif response == cm.NULL : print("Disconnected while reading checking chip");return False,"Don't have CHIP"
    else : print("IC-CHIP presente");name = cm.IC_CARD_TYPE.get(response[8]).get(response[9]);return True,name



class Card:

    def __init__(self) -> None:

        self.has_RF,self.rf_type = has_RF()

        self.has_IC,self.ic_type = has_IC()

        self.cardNumber = ""

        self.cardExpiredDate =""

        self.cardReleaseDate =""

        self.cardHolderName =""

        self.cardValidity = False



        # Hex oppure in asci

    def hexToChar(self,response,i,character):

        str = ""

        if character:

            for j in range(response[i+1]) : str += chr(response[i+2+j]) ; str += " "

        else:

            for j in range(response[i+1]):

                if len('%x'% response[i+2+j]) == 1 : str+= "0"+'%x'% response[i+2+j]+" "

                else : str+= '%x'% response[i+2+j] ; str += " "

        return str

    

        # Per ogni record, controllo se all'interno ottengono queste variabili

    def analyzeSFI(self,response):
        for hex in range(len(response)):

            if response[hex] == 0x5F:

                if response[hex+1] == 0x20 : self.cardHolderName = self.hexToChar(response,hex+1,True)

                elif response[hex+1] == 0x25 : self.cardReleaseDate = self.hexToChar(response,hex+1,False)

                elif response[hex+1] == 0x24 : self.cardExpiredDate = self.hexToChar(response,hex+1,False)

                elif response[hex+1] == 0x28 : self.country = self.hexToChar(response,hex+1,False)



            if response[hex]== 0x5A: # Un check di sicurezza

                if (0x07 <= response[hex+1] <= 0x0A) : self.cardNumber = self.hexToChar(response,hex,False).replace(" ","")

    

        # Valore finale da aggiungere come conferma dell'invio->recezione ( xor tra tutti i valori)

    def bcc(self,byteBCC):

        result = 0x00

        for i in range(len(byteBCC)):

            result ^= byteBCC[i]


            if byteBCC[i] == 0x00:

                if byteBCC[i+1] == 0x03:

                    result ^= byteBCC[i+1] 
                    break

        return result



        # Mando richieste di lettura per i diversi record in memoria che ho trovato

    def readRecords(self,recordList,IC):

        for i in range(len(recordList)):

            number_records_to_read = (recordList[i][2]-recordList[i][1])+1

            if IC :

                byte_array_to_modify = bytearray(cm.IC_ASK_BINARY)

            else:

                byte_array_to_modify = bytearray(cm.RF_ASK_BINARY)

            for j in range(number_records_to_read):


                first_value = (recordList[i][1]+j)# Inizio

                second_value = (recordList[i][0])# Fine

                byte_array_to_modify[8] = first_value

                byte_array_to_modify[9] = second_value

                byte_array_to_modify[12] = self.bcc(byte_array_to_modify)# BCC sicurezza di trasmissione
                if len(self.cardNumber) == 0  or len(self.cardExpiredDate) == 0:
                    response = sendCommand(bytes(byte_array_to_modify))[8:]
                    if response != cm.NULL:
                        self.analyzeSFI(response)
                    else:
                        print("Disconnected while reading records")
                        break

        

        # E' come eseguire una transazione, alcune carte necessitano di questi valori per risalire al numero della carta in se

    def buildingPDOL(self,response,IC):


        bytetoread = response[0]        

        response = response[1:]

        get_record_lenght = 2

        data_record_lenght = 0

        data_lenght = 10

        if IC : starting_hex = [x for x in list(cm.IC_PDOL[0:10])]

        else :starting_hex = [x for x in list(cm.RF_PDOL[0:10])]

        things_to_add = []

        for i in range(bytetoread):

            if response[i] in cm.PDOL_HEX: # Codice Ã¨ presente nel dizionario ( che puÃ² essere ampliato a seconda della carta )

                container = cm.PDOL_HEX.get(response[i])



                if type(container) == dict: # Se nel dizionarion Ã¨ presente una sottocategoria ( che puÃ² essere ampliata a seconda della carta )

                    if response[i+1] in container : container = container.get(response[i+1])

                    else : print("Devo aggiungere:  ",response[i+1], " in ", response[i])



                get_record_lenght+=len(container)

                data_record_lenght+=len(container)

                data_lenght+=len(container)

                for hex in container: things_to_add.append(hex)

        for i in range(2):
            new_starting_hex = starting_hex
            if i == 0:

                new_starting_hex[2] = data_lenght

                new_starting_hex.append(get_record_lenght)

                new_starting_hex.append(0x83)

                new_starting_hex.append(data_record_lenght)

                new_starting_hex = new_starting_hex+things_to_add

                new_starting_hex.append(0x03)

                new_starting_hex.append(self.bcc(new_starting_hex))

                for i in range(64-len(new_starting_hex)): # Sto riempiendo i 64 byte totali da inviare

                    new_starting_hex.append(0x00)

                response = sendCommand(bytes(new_starting_hex))

                printByteString(response)

                if response[8] == 0x67:
                    continue
                else:
                    break

            
            else:
                new_starting_hex[2] = data_lenght+1

                starting_hex = new_starting_hex+things_to_add

                starting_hex.append(0x00)

                starting_hex.append(0x03)

                starting_hex.append(self.bcc(starting_hex))

                for i in range(64-len(starting_hex)): # Sto riempiendo i 64 byte totali da inviare

                    starting_hex.append(0x00)

                response = sendCommand(bytes(starting_hex))

                printByteString(response)

        return response

    

        #PuÃ² essere che riusciamo a trovare la carta prima del "GET RECORD COMMAND"

    def getDataFromPDOL(self,response):

        lenghtT2 = response[0]

        hex_string  = ''.join(format(response[i+1],'02x')for i in range(lenghtT2))

        hex_string = hex_string.split("d",maxsplit=1)

        self.cardNumber = hex_string[0].replace(" ","")

        self.cardExpiredDate = hex_string[1][0:2]+" "+hex_string[1][2:4]

        

        #AFL Ã¨ l'unico che ci interessa, possiamo estrapolare la posizione di records al suo interno 

    def getAIPAFL(self,response):

        printByteString(response)
        
        if response[8] == 0x77:
            i = 0

            aip_hex = False

            afl_hex = False

            fast_card_hex = False

            newList = []

            while i < (len(response)):

                #AIP

                if response[i] == cm.AIP_HEX and not aip_hex:

                    aip_hex = True

                    lenghtAIP = response[i+1]

                    print("AIP : ",end="")

                    for j in range(lenghtAIP):

                        print("%x"%response[j+i+1],end=" ")

                    print()

                    i+=4

                #AFL LIST [NÂ° REGISTRO, INIZIO, FINE , SICUREZZA ?]

                if response[i] == cm.AFL_HEX and not afl_hex:

                    afl_hex = True

                    lenghtAFL = response[i+1]

                    print("AFL : ")

                    newList = []

                    for j in range(0,(lenghtAFL),4):

                        newList.append([response[i+j+x+2] for x in range(4)])



                    for item in range(len(newList)):

                        newList[item][0] = newList[item][0]+4

                #CARTA + SCADENZA

                if response[i] == cm.FAST_CARD_HEX and not fast_card_hex:

                    fast_card_hex = True
                    self.getDataFromPDOL(response[i+1:])

                i+=1
        else:
            lenghtAFL = response[9]-2

            print("AFL : ")

            newList = []

            for j in range(0,(lenghtAFL),4):

                newList.append([response[j+x+12] for x in range(4)])

            for item in range(len(newList)):

                newList[item][0] = newList[item][0]+4

        print(newList)

        return newList

    

        # Dopo essere entrati dentro con AIP, posso vedere se necessita condizione di PDOL o no

    def retrieveInformationIC(self,response):

        pdol = False

        index_lenght_pdol = 0

        for i in range(len(response)):

            if response[i] == 0x9F:

                if response[i+1] == 0x38:

                    print("Necessita di PDOL")

                    pdol = True

                    index_lenght_pdol = i+2

                    break

        if pdol : response = self.buildingPDOL(response[index_lenght_pdol:],True)

        else : response = sendCommand(cm.IC_PDOL)



        if response[8] == cm.MORE_DATA :response = sendCommand(cm.IC_GET_RESPONSE)

        if response != cm.NULL :

            list_of_records = self.getAIPAFL(response) # Qua potrei inserire un blocco di self.readRecords, se la funzione precedentemente ha trovato il valore 0x57

            self.readRecords(list_of_records,True)

                

        #Separo carte che necessitano di un codice speciale per avviare la transazione

    def retrieveInformationRF(self,response):


        pdol = False

        index_lenght_pdol = 0

        for i in range(len(response)):

            if response[i] == 0x9F:

                if response[i+1] == 0x38:

                    print("Necessita di PDOL")

                    pdol = True

                    index_lenght_pdol = i+2

                    break

        if pdol : response = self.buildingPDOL(response[index_lenght_pdol:],False)

        else : response = sendCommand(cm.RF_PDOL)



        if response[8] == cm.MORE_DATA : response = sendCommand(cm.RF_GET_RESPONSE)

        if response != cm.NULL :

            list_of_records = self.getAIPAFL(response)

            self.readRecords(list_of_records,False)


    def use_IC(self):
        if self.has_IC:

            response = sendCommand(cm.COLD_RESET_3V_COMMAND)

            if response != cm.NULL:

                response = sendCommand(cm.IC_COMMAND_VISA)

                if response[8] == cm.FILE_NOT_FOUND : response = sendCommand(cm.IC_COMMAND_MC)

                if response[8] == cm.MORE_DATA : self.retrieveInformationIC(sendCommand(cm.IC_GET_RESPONSE)[8:])

                elif response[8] == cm.FILE_NOT_FOUND : print("AID non presente nel database / Non è una carta di credito")

                elif response == cm.NULL:
                    pass

                else : self.retrieveInformationIC(response[8:])



    def use_RF(self):
        if self.has_RF:

            response = sendCommand(cm.RF_ACTIVATE_COMMAND)

            if response != cm.NULL:

                if "CPU" in self.rf_type :

                    response = sendCommand(cm.RF_COMMAND_VISA)


                    if response[8] == cm.FILE_NOT_FOUND : response = sendCommand(cm.RF_COMMAND_MC)

                    if response[8] == cm.MORE_DATA : self.retrieveInformationRF(sendCommand(cm.RF_GET_RESPONSE)[8:])

                    elif response[8] == cm.FILE_NOT_FOUND : print("AID non presente nel database / Non è una carta di credito")
                    
                    elif response == cm.NULL:
                        pass
                    
                    else : self.retrieveInformationRF(response[8:])



                elif "Mifare one" in self.rf_type : print("This is not a credit card")

                else :
                    print("Brudar, what is this????????????????")
                    sendCommand(cm.RF_DEACTIVATE)
                    self.use_IC()



    def checkCardDate(self):

        

        if len(self.cardExpiredDate) == 5 : self.cardExpiredDate = (self.cardExpiredDate+"-31").replace(" ","-")

        else : self.cardExpiredDate = self.cardExpiredDate.replace(" ","-")[:-1]
        
        print(self.cardExpiredDate)

        print("Year-month-day")

        date = datetime.strptime(self.cardExpiredDate,'%y-%m-%d').date()

        if date <= datetime.today().date() : print("CARTA SCADUTA");self.cardValidity = False

        else : print("CARTA ANCORA VALIDA");self.cardValidity = True


    def checkCardName(self):
        with open("./Commands_Variable/cards_accepted.txt","r") as cn:
            card_name = cn.readlines()
            cn.close()
        card_name = [c.replace("\n","") for c in card_name]
        return card_name

        #Simple print of what i got
    def checkValidity(self):
        found = 0
        card_found = None
        cards_name = self.checkCardName()

        for bin in update.bank_db:
            if self.cardNumber[0:6] in bin:
                print(self.cardNumber[0:6]+" "+bin)
                card_found = bin

        if card_found != None:
            for card in cards_name:
                print(card.lower()+" "+bin.lower())
                if card.lower() in card_found.lower():
                    if self.cardValidity:
                        writeCardStatus("1")
                        found = 1
                        break
                    else:
                        writeCardStatus("4")
                        found = 1
                        break
            if not found:
                writeCardStatus("2")
        else:
            writeCardStatus("3")

    def printData(self):

        print(self.cardHolderName)

        print(self.cardNumber)
        
        if len(self.cardExpiredDate) != 0 :
            self.checkCardDate()
        else:
            print("Nessuna data di scadenza trovata")

        if len(self.cardNumber) < 6 :

            print("Nessun numero trovato")

        else:
            self.checkValidity()

    def getBankName(self):

        if self.has_RF: 

            self.use_RF()

            self.printData()

        elif self.has_IC:

            self.use_IC()

            self.printData()

    def endingUnlocking(self):

        sendCommand(cm.AUTO_LOCK_ON_COMMAND)
        sendCommand(cm.CLOSE_COMMAND)
        sendCommand(cm.OPEN_COMMAND)


if __name__ == "__main__":

    inizializzazione()

    stillConnected = True

    while True:

        try:
            usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
            stillConnected = True

        except usb.USBError:
            stillConnected = False


        if stillConnected:

            if cardIsInside():
                
                writeCardStatus("0")

                card = Card()

                card.getBankName()

                card.endingUnlocking()


        else : connect()

        schedule.run_pending()
                    
        time.sleep(2)







