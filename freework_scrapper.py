import requests
import os
import sys
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
    
    lst = []
    
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
        
        # Créer l'instance Job
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


def load_existing_jobs():
    """Charge les signatures des jobs déjà présents dans le CSV
    
    Returns:
        set: Ensemble des signatures (title|company|published_At)
    """
    if not CSV_FILE.exists():
        return set()
    
    existing_signatures = set()
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                signature = f"{row['title']}|{row['company']}|{row['published_At']}"
                existing_signatures.add(signature)
        
        logger.info(f"Chargement de {len(existing_signatures)} jobs existants")
    except Exception as e:
        logger.error(f"Erreur lors du chargement des jobs existants : {e}")
    
    return existing_signatures


def main():
    """Fonction principale pour récupérer et enregistrer les offres"""
    page = 1
    consecutive_duplicate_pages = 0  # Compteur de pages consécutives avec 100% de doublons
    MAX_CONSECUTIVE_DUPLICATES = 2   # Nombre de pages consécutives identiques avant d'arrêter
    
    while True:
        logger.info(f'Récupération de la page {page}...')
        dta = fetch_page_data(page=page)
        
        if not dta or not dta.get("hydra:member"):
            logger.info('Plus de données disponibles.')
            break
        
        # Créer les instances Job
        jobs = create_dataclass_instance(dta["hydra:member"])
        
        # Charger les jobs existants pour détecter les doublons
        existing_jobs = load_existing_jobs()
        
        # Créer les signatures des nouveaux jobs
        new_signatures = [f"{j.title}|{j.company}|{j.published_At}" for j in jobs]
        
        # Calculer le pourcentage de doublons
        duplicate_count = sum(1 for sig in new_signatures if sig in existing_jobs)
        duplicate_percentage = (duplicate_count / len(new_signatures)) * 100 if new_signatures else 0
        
        logger.info(f"Page {page} : {duplicate_count}/{len(new_signatures)} doublons ({duplicate_percentage:.1f}%)")
        
        # Si 100% de doublons, incrémenter le compteur
        if duplicate_percentage == 100:
            consecutive_duplicate_pages += 1
            logger.warning(f"Page entièrement dupliquée ({consecutive_duplicate_pages}/{MAX_CONSECUTIVE_DUPLICATES})")
            
            # Si on a atteint le seuil, on arrête
            if consecutive_duplicate_pages >= MAX_CONSECUTIVE_DUPLICATES:
                logger.info(f"Arrêt : {MAX_CONSECUTIVE_DUPLICATES} pages consécutives identiques détectées.")
                break
        else:
            # Réinitialiser le compteur si on trouve de nouveaux jobs
            consecutive_duplicate_pages = 0
            
            # Filtrer pour ne garder que les nouveaux jobs
            new_jobs = [j for j, sig in zip(jobs, new_signatures) if sig not in existing_jobs]
            
            if new_jobs:
                if CSV_FILE.exists():
                    _append_lines_on_csv(Job, new_jobs)
                else:
                    _create_and_write_csv(Job, new_jobs)
                
                logger.success(f"Page {page} : {len(new_jobs)} nouveaux jobs enregistrés")
            else:
                logger.info(f"Page {page} : aucun nouveau job à enregistrer")
        
        page += 1
        
        # Délai aléatoire entre les requêtes
        delay = random.uniform(3, 10)
        logger.info(f'Pause de {delay:.1f} secondes...')
        time.sleep(delay)
    
    logger.success(f'Scraping terminé ! Total de pages traitées : {page - 1}')
    
    # Statistiques finales
    if CSV_FILE.exists():
        count = 0
        with open(CSV_FILE, 'r') as f:
            for line in f:
                count += 1
        total_jobs = count - 1  # -1 pour le header # -1 pour le header
        logger.success(f'Total de jobs uniques dans le CSV : {total_jobs}')


if __name__ == '__main__':
    main()