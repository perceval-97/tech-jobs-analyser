import requests
import os
import sys
from dotenv import load_dotenv
from loguru import logger
from dataclasses import dataclass, field, asdict
from datetime import datetime
import time
import random
import html
import re
import pandas as pd
from database.loader import load_existing_datas, database_connexion, insert_data_in_table, create_table


logger.remove()
logger.add(sys.stderr, level='INFO')

load_dotenv()



HEADERS = {
    "User-Agent": os.getenv("USER_AGENT"),
    "Accept": "application/ld+json",
    "Accept-Language": "fr",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.free-work.com/fr/tech-it/jobs"
}

@dataclass
class Job():
    id: str
    title: str
    description: str
    location: str
    candidate_profile: str
    published_at: str
    experience_level: str
    min_daily: int = field(default=None)
    max_daily: int = field(default=None)
    min_annual_salary: int = field(default=None)
    max_annual_salary: int = field(default=None)
    type: str = field(default=None)
    platform: str = field(default='Freework')
    company: str = field(default=None)


PARAMS = {
    "page": 1,
    "itemsPerPage": 16,
    "locationKeys": "fr~~~",
    "searchKeywords": "data"
}

URL = 'https://www.free-work.com/api/job_postings'


def fetch_page_data(page=1):
    """Récupérer les données sur une page"""
    try:
        with requests.Session() as s:
            params = PARAMS.copy()
            params["page"] = page
            
            r = s.get(url=URL, params=params, headers=HEADERS)
            r.raise_for_status()

            data = r.json()

            if data:
                logger.success('Connexion réussie : Données récupérées.')
                return data
            else:
                logger.warning('Data vide')
                return None
    
    except requests.RequestException as e:
        logger.error(f'Erreur lors de la requête page {page}: {e}')
        return None


def clean_html_text(text):
    """Nettoie le texte HTML"""
    if not text:
        return 'N/A'
    
    # Décoder les entités HTML échappées
    text = text.encode().decode('unicode_escape')
    
    # Décoder les entités HTML
    text = html.unescape(text)
    
    # Retirer toutes les balises HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Nettoyer les espaces multiples et sauts de ligne
    text = ' '.join(text.split())
    
    return text


def create_dataclass_instance(data) -> list[dataclass]:
    """Crée une liste d'instances Job à partir des données
    
    Args:
        data: Liste des offres sur une page
    
    Returns:
        list[dataclass]: Liste d'instances dataclass (jobs)
    """
    
    lst = []
    
    for item in data:
        job_id = item.get('id')
        if not job_id:
            logger.warning('No id — job ignoré')
            continue

        # Location
        location = item.get('location', {}).get('label')
        if not location:
            logger.warning('No location')
            location = 'N/A'
        
        # Description (nettoyée)
        description = item.get('description')
        if description:
            description = clean_html_text(description)
            logger.success('Description ajoutée et nettoyée')
        else:
            logger.warning('No description')
            description = 'N/A'
        
        # Company
        company_name = item.get('company', {}).get('name')
        if not company_name:
            logger.warning('No company name')
            company_name = 'N/A'
        
        # Date de publication
        published_at = item.get('publishedAt')
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at)
                published_at = dt.strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                logger.warning('PublishedAt invalide, conservé tel quel')
                published_at = 'N/A'
        else:
            published_at = 'N/A'
        
        # Salaires
        min_annual = item.get('minAnnualSalary', 'N/A')
        max_annual = item.get('maxAnnualSalary', 'N/A')
        min_daily = item.get('minDailySalary', 'N/A')
        max_daily = item.get('maxDailySalary', 'N/A')
        
        # Experience level
        exp_level = item.get('experienceLevel')
        if not exp_level:
            logger.warning('No experience level')
            exp_level = 'N/A'
        
        # Profil candidat (nettoyé)
        profile = item.get('candidateProfile')
        if profile:
            profile = clean_html_text(profile)
        else:
            logger.warning('No profil')
            profile = 'N/A'
        
        # Titre
        title = item.get('title')
        if not title:
            logger.warning('No title')
            title = 'N/A'
        
        # Créer l'instance Job
        job = Job(
            id=str(job_id),
            title=title,
            description=description,
            location=location,
            candidate_profile=profile,
            published_at=published_at,
            experience_level=exp_level,
            min_daily=min_daily,
            max_daily=max_daily,
            min_annual_salary=min_annual,
            max_annual_salary=max_annual,
            company=company_name
        )
        
        lst.append(job)
        logger.success(f"Job traité : {title} chez {company_name}")
    
    return lst



def main():
    """Fonction principale pour récupérer et enregistrer les offres"""
    page = 1
    consecutive_duplicate_pages = 0
    MAX_CONSECUTIVE_DUPLICATES = 2
    db_url = os.getenv('DATABASE_URL')
    
    engine = database_connexion(db_url)
    table = create_table(engine)
    existing_jobs = load_existing_datas(engine)
    
    while True:
        logger.info(f'Récupération de la page {page}...')
        dta = fetch_page_data(page=page)
        
        if not dta or not dta.get("hydra:member"):
            logger.info('Plus de données disponibles.')
            break
        
        jobs = create_dataclass_instance(dta["hydra:member"])
        new_jobs = [j for j in jobs if f"{j.title}|{j.company}|{j.published_at}" not in existing_jobs]
        duplicate_count = len(jobs) - len(new_jobs)
        duplicate_percentage = (duplicate_count / len(jobs)) * 100 if jobs else 0

        logger.info(f"Page {page} : {duplicate_count}/{len(jobs)} doublons ({duplicate_percentage:.1f}%)")
        
        if duplicate_percentage == 100:
            consecutive_duplicate_pages += 1
            logger.warning(f"Page entièrement dupliquée ({consecutive_duplicate_pages}/{MAX_CONSECUTIVE_DUPLICATES})")
            
            if consecutive_duplicate_pages >= MAX_CONSECUTIVE_DUPLICATES:
                logger.info(f"Arrêt : {MAX_CONSECUTIVE_DUPLICATES} pages consécutives identiques détectées.")
                break
        else:
            consecutive_duplicate_pages = 0
            
            if new_jobs:
                df = pd.DataFrame([asdict(j) for j in new_jobs])
                insert_data_in_table(engine=engine, df=df, table=table)
                # mettre à jour existing_jobs 
                existing_jobs.update({f"{j.title}|{j.company}|{j.published_at}" for j in new_jobs})
                logger.success(f"Page {page} : {len(new_jobs)} nouveaux jobs enregistrés")
            else:
                logger.info(f"Page {page} : aucun nouveau job à enregistrer")
        
        page += 1
        delay = random.uniform(3, 10)
        logger.info(f'Pause de {delay:.1f} secondes...')
        time.sleep(delay)
    
    logger.success(f'Scraping terminé ! Total de pages traitées : {page - 1}')




if __name__ == '__main__':
    main()

