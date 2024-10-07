from sqlalchemy import DateTime, create_engine, Column, Integer, String, Text
# Estas son las importaciones necesarias. sqlalchemy 
# proporciona las funcionalidades necesarias para definir 
# modelos de datos y gestionar la base de datos.
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Configurar la base de datos MySQL
# DATABASE_URL = "mysql+pymysql://root:987210@localhost:3306/jobs_db"
DATABASE_URL = "mysql+pymysql://root:@localhost/jobs_db"

# Ejemplo con Server
# DATABASE_URL = "mysql+pymysql://slira:Slira$24@localhost/bd_dev"


# create_engine crea un motor de conexión a la base de datos utilizando la URL proporcionada. 
# declarative_base se utiliza para definir una clase base a partir de la cual se definirán 
# todas las clases de modelos (tablas de la base de datos).
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Definir el modelo de datos
class PreJob(Base):
    __tablename__ = 'pre_jobs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(500), nullable=False)
    job_title = Column(String(500), nullable=False)
    location = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False)
    type_of_job = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    platform = Column(String(100), nullable=False)
    link_url = Column(Text, nullable=False)
    state = Column(Integer, nullable=False)
    keyword = Column(String(100), nullable=True)
    date_scraped = Column(DateTime, nullable=False)

# Crear las tablas
Base.metadata.create_all(engine)

# Configurar la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
