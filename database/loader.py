
# démarre la connexion postgres 
# appelle scraper.py en lui passant la conn


from sqlalchemy import create_engine, MetaData, Table, Integer, String, Column, Date, text, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert



def database_connexion(url):
  engine = create_engine(url)
  return engine


def create_table(engine):
  meta = MetaData()
  
  job_postings = Table('jobs', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('title', String),
    Column('description', String),
    Column('location', String),
    Column('candidate_profile', String),
    Column('published_at', Date),
    Column('experience_level', String),
    Column('min_daily', Float),
    Column('max_daily', Float),
    Column('min_annual_salary', Float),
    Column('max_annual_salary', Float),
    Column('type', String),
    Column('platform', String),
    Column('company', String),
    
    # contrainte d'unicité pour on conflict
    UniqueConstraint('title', 'company', 'published_at', name='uq_job_signature')
    
)
  meta.create_all(engine)
  return job_postings

def insert_data_in_table(engine, df, table):
  with engine.connect() as conn : 
    insert_stmt = insert(table).values(df.to_dict('records'))
    do_nothing_stmt = insert_stmt.on_conflict_do_nothing(index_elements=['title', 'company', 'published_at'])
    conn.execute(do_nothing_stmt)
    conn.commit()


def load_existing_datas(engine):
  with engine.connect() as conn : 
    stmt = text(f'SELECT title, company, published_at FROM jobs')
    datas = conn.execute(stmt)
  return {f"{row[0]}|{row[1]}|{row[2]}" for row in datas}

