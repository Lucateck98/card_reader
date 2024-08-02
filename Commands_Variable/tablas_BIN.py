import requests


def bankUpdate():
    global bank_db
    bank_db = []
    base_url = "https://bintable.com/country/es?page="
    total_pages = 74  # El número total de páginas que deseas descargar
    print("Updating.. Bank Database")
    for page in range(1, total_pages + 1):
        url = base_url + str(page)
        response = requests.get(url,verify=False)
        if response.status_code == 200:
            response = response.text[response.text.rfind("<tbody>"):response.text.find("</tbody")]
            response = (response.replace(" ","")).split("\n")
            response = [x for x in response if x.startswith('<td')]
            for x in range(int(len(response)/5)):
                text = ""
                text+=(response[x*5][response[x*5].find("bin/")+4:response[x*5].find('">')]) #BIN
                text+= " "
                text+=(response[4+x*5][response[4+x*5].find("es/")+3:response[4+x*5].find('">')]).replace("d></td","Bank not specified")  #ISSUER
                bank_db.append(text)
    print("Done !!")
