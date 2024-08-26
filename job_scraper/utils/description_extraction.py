from openai import OpenAI
import json

client = OpenAI(
    api_key="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",
)

#Ejemplo de Uso de Variables de Entorno
#Puedes utilizar el paquete os para manejar las variables de entorno:
#import os  
# import openai
# openai.api_key = os.getenv("OPENAI_API_KEY")
# en el .env: OPENAI_API_KEY=tu_clave_secreta_aqui
#Luego, puedes usar la biblioteca python-dotenv para cargar estas variables en tu script Python:
#from dotenv import load_dotenv
#load_dotenv()


def get_keywords(description, title, company, location):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    Estoy realizando un web scraping de ofertas de trabajo de distintas plataformas laborales. Necesito que identifiques y extraigas las palabras clave de las siguientes categorías de la descripción de trabajo proporcionada: 
                    1. Soft skills
                    2. Hard skills
                    3. Nivel educativo (según esta lista: Estudiante, Egresado y/o Bachiller, Posgrado)
                    4. Profesiones/carreras requeridas
                    5. Si hay información relacionada con LGTBQ+, añade un campo llamado 'LGTBQ+' y llénalo solo con True o False según corresponda.
                    6. Seniority: Entry, Mid, Senior (si es posible). Infiere según el texto de la descripción de trabajo y completa el campo.
                    7. Si hay información sobre la modalidad de trabajo (Presencial, Remoto, Hibrido), añade un campo llamado 'Modalidad de trabajo' y llénalo con el valor correspondiente. Si no hay información, usa 'Presencial'.
                    La oferta puede estar en inglés o español. Si no encuentras información suficiente, infiere según el texto o usa 'no especificado'.

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
                },
            ],
            model="gpt-3.5-turbo",
            temperature=0.7,
            n=2,
        )
        # print(chat_completion.choices[0].message.content.strip())
        # print(chat_completion.choices[1].message.content.strip())    
        responses = chat_completion.choices
        
        # Post-procesamiento para combinar y asegurar extracción de "hard skills"
        combined_results = {
            "Soft skills": [],
            "Hard skills": [],
            "Nivel educativo": [],
            "Profesiones": [],
            "Modalidad de trabajo": "Presencial",
            "LGTBQ+": False,
            "Seniority": "no especificado"
        }
        
        # Combinar resultados de múltiples respuestas
        for response in responses:
            if not response.message or not response.message.content:
                print("Received an empty response from the API")
                continue            
            try:                
                result = json.loads(response.message.content.strip())
                combined_results["Soft skills"] = list(set(combined_results["Soft skills"] + result["Soft skills"]))
                combined_results["Hard skills"] = list(set(combined_results["Hard skills"] + result["Hard skills"]))
                combined_results["Nivel educativo"] = list(set(combined_results["Nivel educativo"] + result["Nivel educativo"]))
                combined_results["Profesiones"] = list(set(combined_results["Profesiones"] + result["Profesiones"]))
                combined_results["Modalidad de trabajo"] = combined_results["Modalidad de trabajo"] if combined_results["Modalidad de trabajo"] != "Presencial" else result["Modalidad de trabajo"]
                combined_results["LGTBQ+"] = combined_results["LGTBQ+"] or result["LGTBQ+"]
                combined_results["Seniority"] = combined_results["Seniority"] if combined_results["Seniority"] != "no especificado" else result["Seniority"]
            except Exception as e:
                print(f"Error decoding JSON response: {e}")
            
        return combined_results
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None