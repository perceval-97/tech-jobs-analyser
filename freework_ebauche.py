import requests
import os
from dotenv import load_dotenv
import requests 
from loguru import logger
from pprint import pprint
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime
import time
import random
import html
import re
from pathlib import Path
import csv

load_dotenv()

HEADERS = {
    "User-Agent": os.getenv("USER_AGENT"),
    "Accept": "application/ld+json",
    "Accept-Language": "fr",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.free-work.com/fr/tech-it/jobs"
}

@dataclass
class Job() : 
  title : str
  description : str
  location : str
  candidate_profile : str 
  published_At : str
  experience_level : str
  min_daily : int = field(default='N/A') 
  max_daily : int = field(default='N/A')
  min_annual_salary : int = field(default='N/A')
  max_annual_salary : int = field(default='N/A')
  type : str = field(default='N/A') # si pas préciser, valeur = chaine vide 
  platform : str = field(default='Freework')
  company : str = field(default = 'N/A')

CSV_FILE = Path.cwd() / 'freework_jobs.csv'

PARAMS = {
    "page": 1,
    "itemsPerPage": 16,
    "locationKeys": "fr~~~",
    "searchKeywords": "data"
}

URL = 'https://www.free-work.com/api/job_postings'

# fonction pour fetch les données sur une page 
# fonction pour écrire les ddonnées 
# 'title', 'slug', 'description', 'candidateProfile', 'experienceLevel'
# minAnnualSalary', 'maxAnnualSalary', 'minDailySalary', 'maxDailySalary', 'currency', 'duration', 'durationValue'
# 'publishedAt'


def fetch_page_data(page=1):
    """Récupérer les données sur une page"""
    try:
        with requests.Session() as s:  # Utilisation standard
            params = PARAMS.copy()
            params["page"] = page
            
            r = s.get(url=URL, params=params, headers=HEADERS)
            r.raise_for_status()

            data = r.json()

            if data : 
               logger.success('Connexion reussie : Données récupérées.')
               return data
            else : 
               logger.warning('Data Vide')
               return None
    
    except requests.RequestException as e:
        logger.error(f'Erreur lors de la requête page {page}: {e}')
        return None

def create_dataclass_instance(data) -> list[dataclass] :
  """_summary_

  Args:
      data (_type_): listes des offres sur une page

  Returns:
      list[dataclass]: list d'instances dataclass (jobs)
  """
  
  for item in data :
    # location
    location = item.get('location', {}).get('label')
    if location:
        logger.success('Location ajoutée')
    else:
        logger.warning('No location')
        location = 'N/A'

    # description
    description = item.get('description')
    if description:
        # décoder les entités HTML échappées (\u003C → <)
        description = description.encode().decode('unicode_escape')
        
        # décoder les entités HTML (&amp; → &, etc.)
        description = html.unescape(description)
        
        # retirer toutes les balises HTML
        description = re.sub(r'<[^>]+>', '', description)
        
        # nettoyer les espaces multiples et sauts de ligne
        description = ' '.join(description.split())
        
        logger.success('Description ajoutée et nettoyée')
    else:
        logger.warning('No description')
        description = 'N/A'

    # récupérer company name
    company_name = item.get('company', {}).get('name')
    if company_name:
      logger.success('Company name ajouté')
    else:
      logger.warning('No company name')
      company_name = 'N/A'
    
    # date de publication
    published_at = item.get('publishedAt')
    if published_at:
        try:
            dt = datetime.fromisoformat(published_at)
            published_at = dt.strftime('%Y-%m-%d')
            logger.success('PublishedAt ajouté et formaté')
        except (ValueError, AttributeError):
            logger.warning('PublishedAt invalide, conservé tel quel')
    else:
        logger.warning('No publishedAt')
        published_at = 'N/A'
    
    # salary
    min_annual = item.get('minAnnualSalary')
    if min_annual:
        logger.success('Min annual salary ajouté')
    else:
        logger.warning('No minAnnualSalary')
        min_annual = 'N/A'

    max_annual = item.get('maxAnnualSalary')
    if max_annual:
        logger.success('Max annual salary ajouté')
    else:
        logger.warning('No maxAnnualSalary')
        max_annual = 'N/A'

    min_daily = item.get('minDailySalary')
    if min_daily:
        logger.success('Min daily salary ajouté')
    else:
        logger.warning('No minDailySalary')
        min_daily = 'N/A'

    max_daily = item.get('maxDailySalary')
    if max_daily:
        logger.success('Max daily salary ajouté')
    else:
        logger.warning('No maxDailySalary')
        max_daily = 'N/A'
    
    # rajouté experienceLevel  
    exp_level = item['experienceLevel']
    if exp_level : 
      logger.success('Exp rajouté')
    else : 
      logger.warning('No Exp')
      exp_level = 'N/A'

    # rajouté profil
    profile = item['candidateProfile']
    if profile : 
      logger.success('Profil rajouté')
    else : 
      logger.warning('No profil')
      profile = 'N/A'

    # rajouté titre
    title = item['title']
    if title : 
      logger.success('Titre rajouté')
    else : 
      logger.warning('No title')
      title = 'N/A'

  # créer une instance job 
  job = Job(title=title,
              candidate_profile=profile,
              experience_level=exp_level,
              min_daily=min_daily,
              max_daily=max_daily,
              min_annual_salary=min_annual,
              max_annual_salary=max_annual,
              description = description, 
              company= company_name,
              location = location,
              published_At=published_at)
    
  # ajouter cette instance à une liste
  lst = []
  lst.append(job)

  return lst


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

       
     
    
     
     

def main () :
   
   page = 1  
   
   while True: 
       dta = fetch_page_data(page=page)  
       
       if dta and dta.get("hydra:member"):  
           jobs = create_dataclass_instance(dta["hydra:member"])
           
           if CSV_FILE.exists():
               _append_lines_on_csv(Job, jobs)
           else:
               _create_and_write_csv(Job, jobs)
           
           page += 1
           time.sleep(random.uniform(3, 10)) 
          
       else:
           logger.info('Plus de données disponibles.')
           break
  

if __name__ == '__main__' :
  main()




