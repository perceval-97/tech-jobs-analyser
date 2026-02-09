import requests
import os
from dotenv import load_dotenv
from loguru import logger
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
class Job():
    title: str
    description: str
    location: str
    candidate_profile: str
    published_At: str
    experience_level: str
    min_daily: int = field(default='N/A')
    max_daily: int = field(default='N/A')
    min_annual_salary: int = field(default='N/A')
    max_annual_salary: int = field(default='N/A')
    type: str = field(default='N/A')
    platform: str = field(default='Freework')
    company: str = field(default='N/A')

CSV_FILE = Path.cwd() / 'freework_jobs.csv'

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
    
    lst = []  # Créer la liste AVANT la boucle
    
    for item in data:
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
        
        # Créer l'instance Job DANS la boucle
        job = Job(
            title=title,
            description=description,
            location=location,
            candidate_profile=profile,
            published_At=published_at,
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


def _create_and_write_csv(Offre, rows):
    """Crée un nouveau fichier CSV et écrit les données"""
    logger.info('Création de fichier CSV')
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [f.name for f in fields(Offre)]
        
        # Écriture du header
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Écriture des lignes
        for item in rows:
            writer.writerow(asdict(item))
    
    logger.success('Création & écriture de fichier : TERMINÉ')


def _append_lines_on_csv(Offre, rows):
    """Ajoute des lignes au fichier CSV existant"""
    logger.info('Ajout de lignes au fichier CSV')
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = [f.name for f in fields(Offre)]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Écriture des lignes
        for item in rows:
            writer.writerow(asdict(item))
    
    logger.success('Écriture de nouvelles lignes : TERMINÉ')


def main():
    """Fonction principale pour récupérer et enregistrer les offres"""
    page = 1
    
    while True:
        logger.info(f'Récupération de la page {page}...')
        dta = fetch_page_data(page=page)
        
        if dta and dta.get("hydra:member"):
            # Vérifier que la liste n'est pas vide
            if len(dta["hydra:member"]) == 0:
                logger.info('Page vide, arrêt de la pagination')
                break
            
            jobs = create_dataclass_instance(dta["hydra:member"])
            
            if CSV_FILE.exists():
                _append_lines_on_csv(Job, jobs)
            else:
                _create_and_write_csv(Job, jobs)
            
            logger.info(f'Page {page} traitée : {len(jobs)} jobs enregistrés')
            page += 1
            
            # Délai aléatoire entre les requêtes
            delay = random.uniform(3, 10)
            logger.info(f'Pause de {delay:.1f} secondes...')
            time.sleep(delay)
        else:
            logger.info('Plus de données disponibles.')
            break
    
    logger.success(f'Scraping terminé ! Total de pages traitées : {page - 1}')


if __name__ == '__main__':
    main()
    