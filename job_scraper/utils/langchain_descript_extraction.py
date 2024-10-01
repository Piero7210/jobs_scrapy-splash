from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
import json
# from dotenv import load_dotenv

# Cargar la API Key desde las variables de entorno
# load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY")

api_key = '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'
# Configurar el cliente de OpenAI con LangChain
llm = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo", temperature=0.7)

# Definir la plantilla del prompt
prompt_template = """
    Estoy realizando un web scraping de ofertas de trabajo de distintas plataformas laborales. Necesito que identifiques y extraigas las palabras clave de las siguientes categorías de la descripción de trabajo proporcionada:
    1. Soft skills
    2. Hard skills
    3. Nivel educativo (según esta lista: Estudiante, Egresado y/o Bachiller, Posgrado)
    4. Profesiones/carreras requeridas
    5. Si hay información relacionada con LGTBQ+, añade un campo llamado 'LGTBQ+' y llénalo solo con True o False según corresponda.
    6. Seniority: Entry, Mid, Senior (si es posible). Infiere según el texto de la descripción de trabajo y completa el campo.
    7. Si hay información sobre la modalidad de trabajo (Presencial, Remoto, Hibrido), añade un campo llamado 'Modalidad de trabajo' y llénalo con el valor correspondiente. Si no hay información, usa 'Presencial'.

    Ejemplo 1:
    Puesto: Desarrollador de Software
    Compañía: Empresa X
    Ubicación: Lima, Perú
    Descripción:
    "Buscamos un desarrollador de software con habilidades en trabajo en equipo, resolución de problemas y conocimiento avanzado en Python y SQL. Requerimos que sea Bachiller en Ingeniería de Sistemas o carreras afines. Es un plus si tiene experiencia con tecnologías en la nube. Valoramos un ambiente inclusivo y LGTBQ+ friendly. La modalidad de trabajo es hibrido."

    Resultados Esperados:
    {{
        "Soft skills": ["trabajo en equipo", "resolución de problemas"],
        "Hard skills": ["Python", "SQL", "tecnologías en la nube"],
        "Nivel educativo": ["Bachiller"],
        "Profesiones": ["Ingeniería de Sistemas"],
        "Modalidad de trabajo": "Hibrido",
        "LGTBQ+": true,
        "Seniority": "no especificado"
    }}

    Ejemplo 2:
    Puesto: Administrador de Empresas
    Compañía: Empresa Y
    Ubicación: Arequipa, Perú
    Descripción:
    "Buscamos un administrador de empresas con habilidades de liderazgo, comunicación efectiva y capacidad de análisis. Requerimos que sea Egresado en Administración de Empresas o carreras afines. Valoramos un ambiente inclusivo y LGTBQ+ friendly. La modalidad de trabajo es en remoto."

    Resultados Esperados:
    {{
        "Soft skills": ["liderazgo", "comunicación efectiva", "capacidad de análisis"],
        "Hard skills": [],
        "Nivel educativo": ["Egresado"],
        "Profesiones": ["Administración de Empresas"],
        "Modalidad de trabajo": "Remoto",
        "LGTBQ+": true,
        "Seniority": "no especificado"
    }}                    

    Oferta de trabajo:
    Puesto: {title}
    Compañía: {company}
    Ubicación: {location}
    Descripción: {description}

    Resultados:
    {{
        "Soft skills": [],
        "Hard skills": [],
        "Nivel educativo": [],
        "Profesiones": [],
        "Modalidad de trabajo": "Presencial",
        "LGTBQ+": false,
        "Seniority": "no especificado"
    }}
"""

# Crear la plantilla de prompt con LangChain
prompt = ChatPromptTemplate.from_template(template=prompt_template)

# Crear la cadena de LangChain
chain = LLMChain(llm=llm, prompt=prompt)

def get_keywords(description, title, company, location):
    try:
        # Ejecutar la cadena con los valores proporcionados
        chat_completion = chain.run({
            "title": title,
            "company": company,
            "location": location,
            "description": description
        })
        
        # Parsear la respuesta JSON
        combined_results = {
            "Soft skills": [],
            "Hard skills": [],
            "Nivel educativo": [],
            "Profesiones": [],
            "Modalidad de trabajo": "Presencial",
            "LGTBQ+": False,
            "Seniority": "no especificado"
        }

        try:
            result = json.loads(chat_completion.strip())
            combined_results["Soft skills"] = result.get("Soft skills", [])
            combined_results["Hard skills"] = result.get("Hard skills", [])
            combined_results["Nivel educativo"] = result.get("Nivel educativo", [])
            combined_results["Profesiones"] = result.get("Profesiones", [])
            combined_results["Modalidad de trabajo"] = result.get("Modalidad de trabajo", "Presencial")
            combined_results["LGTBQ+"] = result.get("LGTBQ+", False)
            combined_results["Seniority"] = result.get("Seniority", "no especificado")
        except Exception as e:
            print(f"Error decoding JSON response: {e}")
        
        return combined_results
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None
