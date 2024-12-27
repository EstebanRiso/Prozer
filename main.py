import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from fastapi import FastAPI
from pydantic import BaseModel
import os
from collections import deque
from typing import Any
from transformers import pipeline
from dotenv import load_dotenv
from db_utils import (
    init_db,
    save_scrape_data, save_process_data, save_combined_data,
    get_scrape_data, get_process_data, get_combined_data
)
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, AutoModelForSeq2SeqLM

tokenizer = AutoTokenizer.from_pretrained("lmsys/fastchat-t5-3b-v1.0", legacy=False)
model = AutoModelForSeq2SeqLM.from_pretrained("lmsys/fastchat-t5-3b-v1.0")




app=FastAPI()
driver_path = "C:/Program Files (x86)/ChromeDriver/chromedriver.exe"  # Reemplaza con la ruta de tu chromedriver
chrome_options = Options()
chrome_options.add_argument("--headless")



is_m2= r"(?i)(\d+(?:\.\d+)?)\s*m[²2t]?"
is_uf = r"(?i)\(?\s*([\d.]*)\s*(uf|unidades de fomento)\s*([\d.]*)\s*\)?"
type_regex = r"(?i)(casas?|departamentos?|deptos?)"





class Url(BaseModel):
    url: str


class UfM2TipoItem(BaseModel):
    uf: int
    m2: int
    tipo: str


class Query_Combined(BaseModel):
    url: str 
    query: str



class Process_Query(BaseModel):
    query: str
    data: list[UfM2TipoItem]



@app.on_event("startup")
def startup_event():
    init_db()


def has_uf_and_m2(tag):
 
    text = tag.get_text(strip=True)
    found_uf = re.search(is_uf, text)
    found_m2 = re.search(is_m2, text)
    return bool(found_uf and found_m2)


def find_minimal_containers_with_uf_and_m2(root):

    queue = deque([root])
    results = []

    while queue:
        current = queue.popleft()

        if has_uf_and_m2(current):
            # Revisamos si algún hijo directo también cumple
            children_that_match = [
                child
                for child in current.find_all(recursive=False)
                if has_uf_and_m2(child)
            ]
            if children_that_match:
                # NO guardamos `current` porque hay hijos más específicos
                # pero seguimos el BFS en esos hijos
                for c in children_that_match:
                    queue.append(c)
            else:
                # Ningún hijo directo cumple => contenedor mínimo
                results.append(current)
        else:
            # Este tag no cumple => hay que seguir buscando en sus hijos
            children = current.find_all(recursive=False)
            for child in children:
                queue.append(child)

    return results


@app.post("/scrape")
async def scrape(Url:Url):
     print("la url es: "+str(Url.url))

     is_number = r"^\d+$"

     
     json_scrape=[]
     service = Service(executable_path=driver_path)
     driver = webdriver.Chrome(service=service, options=chrome_options)

     driver.get(Url.url)
     #vamos a esperar 10 segundos para que cargue la página web
     time.sleep(5)

     scroll_pause_time = 3
     last_height = driver.execute_script("return document.body.scrollHeight")

     while True:
          # Desplazarse hasta el final de la página
          driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
          time.sleep(scroll_pause_time)  # Esperar a que el contenido cargue

          # Obtener la nueva altura de la página
          new_height = driver.execute_script("return document.body.scrollHeight")
          if new_height == last_height:
               # Si no hay cambio en la altura, hemos llegado al final
               break
          last_height = new_height

     html_content = driver.page_source

     soup = BeautifulSoup(html_content, "html.parser")
     candidates = soup.find_all(has_uf_and_m2)  

     data = {
          "uf": [],
          "m2": [],
          "tipo": []
     }


     candidates = find_minimal_containers_with_uf_and_m2(soup)
     # Aquí extraes tus datos de c (UF, m2, etc.)

     for candidate in candidates:

          print("Tag:", candidate.name)
          print("Texto:", candidate.get_text(strip=True))

          text= candidate.get_text(strip=True)
          ufs=re.findall(is_uf,text)
          m2s=re.findall(is_m2,text)

          for match in ufs:
               left_num=match[0]
               right_num=match[2]

               chosen=left_num if left_num else right_num
               
               chosen_cleaned=chosen.replace(".","") if chosen else ""

               if chosen_cleaned:
                    data["uf"].append(chosen_cleaned)
          
          for match in m2s:

               m2_cleaned = match.replace(".", "")  # si deseas quitar los puntos
               data["m2"].append(m2_cleaned)


          match_tipo = re.search(type_regex, text)     
          
          if match_tipo:
               found_tipo = match_tipo.group(1).lower()  # 'casa', 'departamento' o 'depto'
               if found_tipo.startswith("casa"):
                    data["tipo"].append("casa")
               elif found_tipo.startswith("depto") or found_tipo.startswith("departamento"):
                    data["tipo"].append("departamento")
               else:
                    data["tipo"].append("desconocido")
          else:
               data["tipo"].append("desconocido")
               

     data["uf"] = list(dict.fromkeys(data["uf"]))
     data["m2"] = list(dict.fromkeys(data["m2"]))

     uf_numbers= [int(x) for x in data['uf']]
     m2_numbers= [int(x) for x in data['m2']]

     for u, m, t in zip(uf_numbers, m2_numbers,data["tipo"]):
          json_scrape.append({
               "uf": u,
               "m2": m,
               "type":t,
          })  

     json_return={"UfM2TipoItem:": json_scrape}

     driver.quit()

     save_scrape_data(payload)
     return json_return

@app.get("/scrape")
def read_scrape():
    
    data = get_scrape_data()
    return data

@app.post("/process")
async def process(Process_Query:Process_Query):
     
     prompt="Dada esta data:\n\n"+str(Process_Query.data)+"\n\n Responde mi consulta:"+str(Process_Query.query)
     
     my_pipeline = pipeline("text2text-generation", model=model, device=-1, tokenizer=tokenizer, max_length=1000)
     
     result = my_pipeline(prompt)

     generated = result[0]["generated_text"]

     return {"Answer": generated}

@app.get("/process")
def read_process():
    data = get_process_data()
    return data


@app.post("/combined")
async def combined(Query_Combined:Query_Combined):

     url=Url()
     url.url=Query_Combined.url
     
     data=scrape(url)

     query_process=Process_Query()
     query_process.query=Query_Combined.query 
     query_process.data=data
     
     json_return=process(query_process)


     return json_return

@app.get("/combined")
def read_combined():
    data = get_combined_data()
    return data

if __name__ == "__main__":
     import uvicorn

     uvicorn.run(app, host="0.0.0.0",port=8000)



