import os
import re
import openai
import pathlib
import requests
import json
import time
import csv
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import tiktoken
import yaml
from yaml import Loader

def fileToString(path):
    with open(path, 'r') as file:
        data = file.read()
    return data

def getOpenAIKey():
    return fileToString(str(pathlib.Path(__file__).parent.resolve()) + '/openai-key.txt')

def getOpenAIModel():
    return "gpt-3.5-turbo-16k"

def countTokens(content):
    enc = tiktoken.encoding_for_model(getOpenAIModel())
    encoded = enc.encode(content)
    #print(len(encoded), 'tokens')
    return len(encoded)

def getLicencesYAML():
    return fileToString(str(pathlib.Path(__file__).parent.resolve()) + '/licences.yaml')

def meta_redirect(url, content):
    #print("meta_redirect", content)
    soup  = BeautifulSoup(content, features="html.parser")
    result=soup.find("meta",attrs={"http-equiv":re.compile("^refresh$", re.I)})
    #print("result", result)
    if result:
        wait,text=result["content"].split(";")
        if text.strip().lower().startswith("url="):
            url2=text.strip()[4:]
            return urljoin(url, url2)
    return None

def getHTML(url):
    r = requests.get(url)
    r.raise_for_status()
    url = meta_redirect(url, r.text)
    if url != None:
        #print("follow url", url)
        return getHTML(url)
    else:
        return r.text

def removeTags(html, all = False):
    soup = BeautifulSoup(html, features="html.parser")
    for script in soup(["script", "style", "meta", "head"]):
        script.extract()
    container = soup.find('body')
    keep = []
    for node in container.descendants:
      if not node.name or (not all and node.name == 'a'):
        keep.append(str(node))
    return str(" ".join(keep))

def removeAllTags(text):
    return removeTags(text, True)

def runTask1(url, html):
    #Task 1: find links including licences and terms and conditions from a web page
    #SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content.
    #USER: Find the link to the pages describing licences, privacy policies, or terms of use of the content in the following HTML source code. Please respond ONLY with a JSON format with a list of maximum 3 links, resolved according to this address: {url} HTML code: {html}
    messages = [
            {"role": "system", "content": "You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content."},
            {"role": "user", "content": f"Find the link to the pages describing licences, privacy policies, or terms of use of the content in the following HTML source code. Please respond ONLY with a JSON format with a list of maximum 3 links, resolved according to this address: {url} HTML code: {html}"}
        ]
    response = openai.ChatCompletion.create(
                #model="gpt-4-0613",
                model=getOpenAIModel(),
                messages=messages,
                # engine=engine
    )
    return response["choices"][0]["message"]["content"]


def loadMusoW():
    with open('Query-16.csv', newline='') as csvfile:
        dataReader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        data = {}
        for row in dataReader:
            # "resource","licence","webpage","label","category","audience","genre","type","licenceLabel"
            if row['resource'] not in data:
                data[row['resource']] = {}
                for col in row:
                    data[row['resource']][col] = set([row[col]])
            else:
                existing = data[row['resource']]
                for col in row:
                    data[row['resource']][col].add(row[col])
    return data

def loadUnknown():
    musoW = loadMusoW()
    tags = ['https://w3id.org/musow/vocab/open-access',
    'https://w3id.org/musow/vocab/not-specified',
    'https://w3id.org/musow/vocab/copyright',
    'https://w3id.org/musow/vocab/unknown-licence',
    'https://w3id.org/musow/vocab/privative']
    unknown = {}
    for ix in musoW:
        for t in tags:
            if t in musoW[ix]['licence']:
                unknown[ix] = musoW[ix]
                break
    return unknown

def executeTask1():
    openai.api_key = getOpenAIKey()
    # links = runTask1("https://musescore.org/", removeTags(getHTML("https://musescore.org/")))
    # for link in links['links']:
    #     print(link)
    unknown = loadUnknown()
    counter = 0
    for ix in unknown:
        try:
            id = ix.replace("https://w3id.org/musow/","")
            fname = 'data/' + id + '.t1.json'
            webpage = next(iter(unknown[ix]['webpage']))
            if pathlib.Path(fname).is_file():
                print(webpage, 'Check existing ...')
                # Check content is good otherwise retry
                previous = json.loads(fileToString(fname))
                try:
                    #previousResponse = json.loads(previous['response'])
                    #print("previous response", previousResponse)
                    previousLinks = urlsInString(previous['response'])
                    if(len(previousLinks) > 0):
                        print(webpage, ' ... ' + str(len(previousLinks)), ' found previously.')
                        continue
                except Exception as tt:
                    print(webpage, ' ... (' + str(tt) + ') response was:', previous['response'])
                print(webpage, 'Try again')
            time.sleep(1)
            htmlcode = removeTags(getHTML(webpage))
            data = {}
            response = runTask1(webpage, htmlcode)
            counter = counter + 1
            data['response'] = response
            data['webpage'] = webpage
            data['htmlcode'] = htmlcode
            with open(fname, 'w', encoding="utf-8") as f:
                json.dump(data, f)
            print(webpage, 'OK')
        except Exception as e:
            print(webpage, 'ERROR: ' + str(e))
        print("OpenAI api called " + str(counter) + ' times')

def urlsInString(string):
    URL_PATTERN = r'.+(http[s]{0,1}://[A-Za-z0-9%-_]+(/[A-Za-z0-9%-_])*(#|\\?)[A-Za-z0-9%-_&=]*).+'
    p = re.compile(URL_PATTERN)
    res = p.findall(string)
    ret = []
    for r in res:
        ret.append(next(iter(r)))
    return ret

def generateT1CSV():
    directory = str(pathlib.Path(__file__).parent.resolve()) + '/data'
    with open(directory + '/T1.csv', 'w', newline='') as csvfile:
        t1writer = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        header = ['resource', 'webpage', 'links', 'niceJSON']
        t1writer.writerow(header)
        for filename in os.listdir(directory):
            f = os.path.join(directory, filename)
            # checking if it is a file
            if os.path.isfile(f) and f.endswith('.t1.json'):
                j = json.loads(fileToString(f))
                resource = filename.replace('.t1.json','')
                webpage = j['webpage']
                response = j['response']
                try:
                    json.loads(response)
                    niceJSON = True
                except Exception as oiu:
                    niceJSON = False                    
                links = " ".join(urlsInString(response))
                t1writer.writerow([resource,webpage,links,niceJSON])
                print(webpage)

def runTask2(text):
    # Task 2: Extract copyright and licences
    #
    #     SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content and express it in JSON format.
    #     USER: Please list the licences, copyright owners, and terms and conditions mentioned in the following text. Respond only with a JSON object with 3 fields, 'copyright', 'licences', and 'terms and conditions'. The text is: {text}
    messages = [
            {"role": "system", "content": "You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content and express it in JSON format."},
            {"role": "user", "content": f"Please list the licences, copyright owners, and terms and conditions mentioned in the following text. Respond only with a JSON object with 3 fields, 'copyright', 'licences', and 'terms and conditions'. The text is: {text}"}
        ]
    response = openai.ChatCompletion.create(
                #model="gpt-4-0613",
                model=getOpenAIModel(),
                messages=messages,
                # engine=engine
    )
    return response["choices"][0]["message"]["content"]

def executeTask2():
    openai.api_key = getOpenAIKey()
    directory = str(pathlib.Path(__file__).parent.resolve()) + '/data'
    with open(directory + '/T1.csv', 'r', newline='') as csvfile:
        t1data = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        counter = 0
        for row in t1data:
            try:
                data = row
                id = row['resource']
                fname = 'data/' + id + '.t2.json'
                webpage = row['webpage']
                atLeastOne = False
                # If file exists, load it and check its content
                if pathlib.Path(fname).is_file():
                    print(webpage, 'Check existing ...')
                    # Check content is good otherwise retry
                    previous = json.loads(fileToString(fname))
                    try:
                        # If links is empty or response is empty, try againg
                        if previous['links'] != "" and len(previous['response']) > 0:
                            # Verify previous response
                            try:
                                
                                for prevLink in previous['response']:
                                    print("... checking ", prevLink['link'])
                                    if len(prevLink['error']) > 0:
                                        print(" ... broken: ", str(prevLink['error']) + " -- file is " + fname)
                                        continue
                                    try:
                                        plr = json.loads(prevLink['response'])
                                        if len(plr['copyright']) > 0:
                                            # check licences
                                            if 'licences' in plr and len(plr['licences']) > 0 or 'licenses' in plr and len(plr['licenses']) > 0:
                                                atLeastOne = True
                                                break
                                    except Exception as yua:
                                        print(" ... broken (" + str(yua) + ") -- was: ", str(prevLink['response']) + " file is " + fname)
                                        # Bad json
                                #print(webpage, ' ... content there previously. ' + str(previous['response']))
                                #continue
                            except Exception as trw:
                                print(webpage, ' ... prev content broken. ' + str(trw) + ' -- was: ' + str(previous['response']))
                    except Exception as tt:
                        print(webpage, ' ... (' + str(tt) + ') response was:', previous['response'])
                    if not atLeastOne:
                        print(webpage, 'RETRY -- ', str(fname))
                    else:
                        print(webpage, 'KEEP -- ', str(fname))
                        continue
                #time.sleep(1)
                #continue
                links = []
                for link in row['links'].split():
                    try:
                        time.sleep(1)
                        error = ""
                        response = ""
                        htmlcode = removeAllTags(getHTML(link))
                        counter = counter + 1
                        response = runTask2(htmlcode)
                    except Exception as ex:
                        error = str(ex)
                    links.append({'link': link,'response': response, 'error': error})
                data['response'] = links
                with open(fname, 'w', encoding="utf-8") as f:
                    json.dump(data, f)
                print(row['webpage'], 'OK')
            except Exception as e:
                print(row['webpage'], 'ERROR: ' + str(e))
            print("OpenAI api called " + str(counter) + ' times')

def generateT2CSV():
    directory = str(pathlib.Path(__file__).parent.resolve()) + '/data'
    with open(directory + '/T2.csv', 'w', newline='') as csvfile:
        t2writer = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        header = ['resource', 'webpage', 'link', 'copyright', 'licence', 'terms', 'error']
        t2writer.writerow(header)
        for filename in os.listdir(directory):
            f = os.path.join(directory, filename)
            # checking if it is a file
            if os.path.isfile(f) and f.endswith('.t2.json'):
                j = json.loads(fileToString(f))
                resource = filename.replace('.t2.json','')
                webpage = j['webpage']
                response = j['response']
                if len(response) > 0:
                    for res in response:
                        link = ""
                        copyright = ""
                        licence = ""
                        terms = ""
                        error="SUCCESS"
                        if len(res['response']) > 0:
                            link = res['link'] 
                            try:
                                resp = json.loads(res['response'])
                                copyright = resp['copyright']
                                licence = resp['licences']
                                if 'terms and conditions' in resp:
                                    terms = resp['terms and conditions']
                            except Exception as ex:
                                error = "ERR_JSON :: " + str(ex)
                        else:
                            error = "ERR_SERVICE :: " + res['error']
                        t2writer.writerow([resource,webpage,link,copyright,licence,terms, error])
                        
                print(webpage)
  

def runTask3(description):
    # Task 3: Link licences to DALICC codes#
    #     SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content. You are also proficient in reading YAML files.
    #     USER: Given the following list of licences, can you tell me to which licence the following description refers to: {{LICENCEEXPR}}
    licy = yaml.load(fileToString('licences.yaml'), Loader=Loader)
    llist = []
    for item in licy:
        llist.append('- [' + item['code'] + '] ' + item['title'] + ' (' + item['publisher'] + ') ' + item['link'])
    listOfLicences = "\n".join(llist)
    #print(listOfLicences)
    messages = [
            {"role": "system", "content": f"You are expert in licencing and terms and conditions of resources on the Web. and know the following list of licences: \n\n {listOfLicences}"},
            {"role": "user", "content": f"Can you tell me to which licences the following licence description refers to? The description is  {description} -- Please respond by only reporting the selected licences from the list or 'NONE' if none is found"}
        ]
    #print("Prompt: ", messages)
    #return "BLA"
    response = openai.ChatCompletion.create(
                #model="gpt-4-0613",
                model=getOpenAIModel(),
                messages=messages,
                # engine=engine
    )
    return response["choices"][0]["message"]["content"]
    
def executeTask3():
    openai.api_key = getOpenAIKey()
    directory = str(pathlib.Path(__file__).parent.resolve()) + '/data'
    with open(directory + '/T2.csv', 'r', newline='') as csvfile:
        t2data = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        # Collect info for each resource
        byResource = {}
        for row in t2data:
            try:
                data = row
                if row['error'] != 'SUCCESS':
                    # Ignore errors
                    continue
                id = row['resource']
                if id not in byResource:
                    byResource[id] = {}
                    byResource[id]['webpage'] = row['webpage']
                if 'licence' not in byResource[id]:
                    byResource[id]['licence'] = []
                if data['licence'] != '[]':
                    byResource[id]['licence'].append(data['licence'])
            except Exception as e:
                print(row['link'], 'ERROR: ' + str(e))
        id = None
        for id in byResource:
            fname = 'data/' + id + '.t3.json'
            description = " ".join(byResource[id]['licence']).strip()
            if len(description) == 0:
                print("no licence info from ", 'data/' + id + '.t2.json')
                continue
            print("Running " + fname, description)
            time.sleep(1)
            byResource[id]['linked_licence'] = runTask3(description)
            print(" ... ", byResource[id]['linked_licence'])
            with open(fname, 'w', encoding="utf-8") as f:
                json.dump(byResource[id], f)
            print(fname, 'OK')
        
def generateT3CSV():
    directory = str(pathlib.Path(__file__).parent.resolve()) + '/data'
    with open(directory + '/T3.csv', 'w', newline='') as csvfile:
        t3writer = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        header = ['resource', 'webpage', 'licence', 'linked_licence']
        t3writer.writerow(header)
        for filename in os.listdir(directory):
            f = os.path.join(directory, filename)
            # checking if it is a file
            if os.path.isfile(f) and f.endswith('.t3.json'):
                j = json.loads(fileToString(f))
                resource = filename.replace('.t3.json','')
                webpage = j['webpage']
                licence = j['licence']
                linked_licence = j['linked_licence']
                t3writer.writerow([resource,webpage,licence,linked_licence])
  

def generateT2ByResourceCSV():
    import pysparql_anything as cli
    engine = cli.SparqlAnything()
    engine.run(q='queryT2data.sparql',o='data/T2_byResource.csv')

def generateT3ByResourceCSV():
    import pysparql_anything as cli
    engine = cli.SparqlAnything()
    engine.run(q='queryT3data.sparql',o='data/T3_byResource.csv')


#executeTask1()
#generateT1CSV()
#executeTask2()
#generateT2CSV()
#executeTask3()
#generateT3CSV()
#generateT2ByResourceCSV()
generateT3ByResourceCSV()

#print(removeTags(getHTML("http://www.schubert-online.at/")))
#countTokens("<!DOCTYPE html>\n\n<html>\n\n<body>\n<!-- This file lives in public/404.html -->\n<div class=\"navbar\" id=\"header-navbar\" role=\"navigation\">\n<div class=\"container\">\n<div class=\"row\" id=\"header-row1\">\n<div id=\"logo-col\">\n<a href=\"https://library.louisville.edu/home\">\n<img alt=\"U of L Libraries\" src=\"/logo-libraries-ALT_white_120w.png\"/>\n<div class=\"visible-xs\" id=\"logo-sm\">\n<img alt=\"U of L Libraries\" src=\"/logo-uofl-ligature-ALT_white_40w.png\"/>\n</div>\n</a>\n<div class=\"navbar-product-name\">\n<a href=\"http://digital.library.louisville.edu/\">\n              Digital Collections\n          </a>\n</div>\n</div>\n</div>\n</div>\n</div>\n<div class=\"container\" id=\"content-wrapper\" role=\"main\">\n<div id=\"error-number\">404</div>\n<h1>The page you were looking for doesn't exist.</h1>\n<div class=\"error-image\">\n<img alt=\"unicorn\" src=\"/500-stephen-leonardi-LzGiBl8DRPM-unsplash-cropped.png\"/>\n</div>\n</div>\n</body>\n</html>\n")
#print(removeAllTags("<!DOCTYPE html>\n\n<html>\n\n<body>\n<!-- This file lives in public/404.html -->\n<div class=\"navbar\" id=\"header-navbar\" role=\"navigation\">\n<div class=\"container\">\n<div class=\"row\" id=\"header-row1\">\n<div id=\"logo-col\">\n<a href=\"https://library.louisville.edu/home\">\n<img alt=\"U of L Libraries\" src=\"/logo-libraries-ALT_white_120w.png\"/>\n<div class=\"visible-xs\" id=\"logo-sm\">\n<img alt=\"U of L Libraries\" src=\"/logo-uofl-ligature-ALT_white_40w.png\"/>\n</div>\n</a>\n<div class=\"navbar-product-name\">\n<a href=\"http://digital.library.louisville.edu/\">\n              Digital Collections\n          </a>\n</div>\n</div>\n</div>\n</div>\n</div>\n<div class=\"container\" id=\"content-wrapper\" role=\"main\">\n<div id=\"error-number\">404</div>\n<h1>The page you were looking for doesn't exist.</h1>\n<div class=\"error-image\">\n<img alt=\"unicorn\" src=\"/500-stephen-leonardi-LzGiBl8DRPM-unsplash-cropped.png\"/>\n</div>\n</div>\n</body>\n</html>\n"))












