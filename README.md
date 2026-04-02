# Indeed Analyser

A data pipeline that scrapes job offers from Freework and loads them
into a PostgreSQL database to analyse the data engineering job market.

## Project Structure

```
jobs-analyser/
├── scraper/          # Scraping scripts
├── database/         # Database models and loaders
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Tech Stack

- **Python** — scraping and data processing
- **PostgreSQL** — data storage
- **SQLAlchemy** — ORM and database interactions
- **Docker / Docker Compose** — containerization

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Python 3.13+

### Installation

1. Clone the repository

```bash
git clone https://github.com/perceval-97/tech-jobs-analyser.git
cd jobs-analyser
```

2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Run with Docker

```bash
docker-compose up --build
```

## What it does

Scrapes job offers from Freework, deduplicates them by
title + company + date, and stores them in PostgreSQL
for analysis of the data engineering job market
(in-demand technologies, salary trends, junior vs senior roles).

## Roadmap

- [x] Freework scraper
- [x] PostgreSQL integration with deduplication
- [x] Docker containerization
- [ ] Airflow orchestration (April 2026)
- [ ] dbt transformations (May 2026)
- [ ] Azure integration (July 2026)

## Author

Amour Hounga — Data Engineer in training  
[https://www.linkedin.com/in/amour-hounga/](#) · [https://github.com/perceval-97](#)
