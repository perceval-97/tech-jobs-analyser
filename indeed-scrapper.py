from playwright.sync_api import sync_playwright, expect
from loguru import logger
import sys
import os 
from dotenv import load_dotenv 
from pathlib import Path
from selectolax.parser import HTMLParser
from random import randint
from dataclasses import dataclass, fields, asdict, field
import csv


 
@dataclass
class Offre():
  name : str
  company : str
  description : str
  lieu : str
  salaire : str = field(default='N/A') 
  type : str = field(default='N/A') # si pas préciser, valeur = chaine vide 
  platform : str = field(default='Indeed') 

# logger config 
logger.remove()
logger.add(sys.stderr, level='INFO')


load_dotenv()

AUTH = os.getenv('AUTH')
TARGET_URL = 'https://fr.indeed.com/'
FILE_PATH = Path.cwd() / 'indeed.html'
CSV_FILE = Path.cwd() / 'indeed_jobs.csv'


"""
- se connecter à la page et recupérer le contenu de la page
- fonction pour récupérer toutes les offres sur une page
- fonction pour écrire le html sur le disque 
- fonction pour passer à la page suivante 
- pour chaque offre, récupérer (titre, description, salaire, company et url)
  - au fur et à mesure qu'on recupère, ecrire dans un csv
"""

def run(pw : sync_playwright, keyword : str, url : str, brigh_data : bool, headless : bool, nbre_iter) -> str:
  """_summary_

  Args:
      pw (sync_playwright): instance playwright
      keyword (str): mot clé de recherche une fois sur indeed
      url (str): url auquel on veut accéder
      brigh_data (bool): si oui / non on passe par le webscrapper de bright_data pour la résolution de captchas
      headless (bool): paramètre headless pour browser sans bright_data

  Returns:
      str: contenu de la page
  """
   
  endpoint_url = f'wss://{AUTH}@brd.superproxy.io:9222'
  
  if brigh_data == True :
    browser = pw.chromium.connect_over_cdp(endpoint_url)
  else : 
    browser = pw.chromium.launch(headless = headless)
    

  
  try  :
    logger.info(f'Connection à {url}')

    page = browser.new_page()
    page.goto(url)
    page.wait_for_timeout(1000)

    # gestion des cookies
    logger.info('Gestion des cookies')
    page.get_by_role("button", name="Paramètres des cookies, Ouvre").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Confirmer").click()
    logger.info('Gestion de cookies terminéé')
    page.wait_for_timeout(1000)

    # keyword researcch
    logger.info(f'Recherche du mot clé {keyword} ')
    page.get_by_role("combobox", name="search: Job title, keywords,").click()
    page.get_by_role("combobox", name="search: Job title, keywords,").fill(keyword)
    page.get_by_role("button", name="Rechercher").click()

    # récupérer la liste des jobs valides et cliquer dessus pour récupérer infos

    for i in range(nbre_iter): 

      logger.info('Tentative de récupération des différentes offres')
      jobs_valids_links = page.locator("a[data-jk]:not([rel='nofollow'])").all()
      logger.info(f'{len(jobs_valids_links)} offres récupérées')
      
      for idx, job_link in enumerate(jobs_valids_links, 1) : 
       
        try : 
          logger.info(f'Page: {i+1} | offre : {idx} / {len(jobs_valids_links)}')
          job_link.click()

          page.wait_for_load_state('networkidle')
          page.wait_for_timeout(randint(500, 1000))

          content = page.content()

          if content : 
            logger.success(f'Contenu de page récupéré')
            infos = get_job_infos(content=content) # -> retourne une liste par page
            
            ### écrire un csv à partir de la liste dans un seul fichier 

            if i == 0 :
              _create_and_write_csv(Offre=Offre, rows=infos)
            else : 
              _append_lines_on_csv(Offre=Offre, rows=infos)

        except Exception as e: 
          logger.warning(f'Impossible de récupérer le contenu de la page {e}')

      # next page button 
      next_btn = page.locator("a[data-testid='pagination-page-next']")
      if next_btn : 
        logger.info('Passage à la page suivante')
        next_btn.click()
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(randint(1000, 2000))
        
      else : 
        logger.info('Plus de page disponible.')
        break


  finally : 
    pass

def _write_content(content) -> None :
  """Ecriture du fichier sur le disque"""
  logger.info('Ecriture du contenu de page en local')
  with open(FILE_PATH, 'w') as f : 
    f.write(content)
  logger.info('Ecriture de fichier : TERMINE')

def _read_content() : 
  logger.info('Lecture du fichier à partir du disque')
  if FILE_PATH : 
    with open(FILE_PATH, 'r') as f : 
      return f.read()
  else : 
    logger.error('Aucun fichier trouvé : LECTURE IMPOSSIBLE')
 
def get_job_infos(content : str) -> list:
  """Récupérer les infos de chaque offre sur une page.
  Args:
      content (str): contenu html de la page

  Returns:
      list: liste d'instance Offre
  """
   
      
  try : 
    tree = HTMLParser(content)

    #récupérer le titre
    title = tree.css_first('h2[data-testid="jobsearch-JobInfoHeader-title"]').text()
    if title : 
      logger.success(f"Titre de l'offre récupéré : {title}")
    else : 
      logger.warning('Titre non récupéré')
      title = 'N/A'

    # get company name 
    company = tree.css_first('div[data-testid="inlineHeader-companyName"]').text()
    if company : 
      logger.success(f"Company name: {company}")
    else :
      logger.warning('Company name non récupéré')
      company = 'N/A'

    #get company location
    location = tree.css_first('div[data-testid="jobsearch-JobInfoHeader-companyLocation"]').text()
    if location : 
      logger.success(f'Location : {location}')
    else : 
      logger.warning('Location non récupéré')
      location = 'N/A'

    #get type
    nodes = tree.css("#jobDetailsSection > li[data-testid='list-item']") # -> list

    if nodes : 
      type_node = nodes[-1]
      type = type_node.css_first('span').text()
      logger.success(f'Type de contrat récupéré : {type}')
    
    else : 
      logger.warning('Pas de nodes pour récupérer le type de contract.')
      type = 'N/A'

    # get description
    description = tree.css_first("#jobDescriptionText").text()
    if description : 
      logger.success(f'Description récupérée.')
    else : 
      logger.error('Description non récupéré.')
      description = 'N/A'
    
    # créer une instance de Offre

    offre_1 = Offre(name=title, 
                    company=company, 
                    description=description, 
                    lieu=location, 
                    type=type)

    # ajouter l'instance à une liste et retourner la liste
    
    lst = []
    lst.append(offre_1)
    logger.info("Ajout de l'instance dataclass dans une liste \n")

    return lst

  except Exception as e : 
    logger.error(f"Erreur lors de la récupération des infos : {e}")
    return []
    
  
def _create_and_write_csv (Offre ,rows) :
  logger.info('Création de fichier csv')
  
  with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:

    fieldnames = [f.name for f in fields(Offre)]

    # écriture du header
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    # écriture des lignes 
    for item in rows : 
      writer.writerow(asdict(item))

  logger.success('Création & écriture de fichier : TERMINE')

def _append_lines_on_csv(Offre,rows) :
  
  logger.info('Ajout de lignes au fichier csv')
  
  with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:

    fieldnames = [f.name for f in fields(Offre)]

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    
    # écriture des lignes 
    for item in rows : 
      writer.writerow(asdict(item))
  
  logger.success('Ecriture de nouvelles lignes : TERMINE')


if __name__ == '__main__' :
  with sync_playwright() as p :
    run(pw=p,
        keyword='software',
        url=TARGET_URL,
        brigh_data = True,
        headless=False, 
        nbre_iter = 10)