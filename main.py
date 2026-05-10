import argparse
import config
from scripts.get_market_data import obtener_datos_preparados
from scripts.get_gameDevMap import obtener_datos_gamedevmap
from scripts.etl_gameDevMap import run_geo_etl
from scripts.etl_igdb import process_studios_to_mdm
from scripts.build_db import build_database
from scripts.audit_data import run_audit

def run_pipeline():
  """
  Ejecuta toda la pipeline de ETL y construcción de la base de datos.
  """

  # --- Configuración de argumentos ---
  parser = argparse.ArgumentParser(description="(Orquestador) Ejecuta la pipeline de ETL y construcción de la base de datos.")

  # Añadimos flags para saltar pasos específicos
  parser.add_argument("--skip-extract", action="store_true", help="Saltar la fase de extracción de datos.")
  parser.add_argument("--skip-transform", action="store_true", help="Saltar la fase de transformación de datos.")
  parser.add_argument("--skip-load", action="store_true", help="Saltar la fase de carga a la base de datos.")
  parser.add_argument("--skip-audit", action="store_true", help="Saltar la fase de auditoría de calidad de datos.")

  args = parser.parse_args()

  # 0. Inicializamos el entorno 
  print("Inicializando entorno...")
  config.init_environment()

  # 1. Extracción de datos
  if not args.skip_extract:
      print("Ejecutando fase de extracción de datos...")
      obtener_datos_preparados()
      obtener_datos_gamedevmap(all_locations=True)  # Obtenemos datos de todas las ubicaciones
      process_studios_to_mdm() # Integración con IGDB para Master Data
  else:
      print("Saltando fase de extracción de datos...")

  # 2. Transformación (ETL)
  if not args.skip_transform:
      print("Ejecutando fase de transformación de datos...")
      run_geo_etl()
  else:
      print("Saltando fase de transformación de datos...")
  
  # 3. Carga a la base de datos
  if not args.skip_load:
      print("Ejecutando fase de carga a la base de datos...")
      build_database()
  else:
      print("Saltando fase de carga a la base de datos...")

  # 4. Auditoría de Datos
  if not args.skip_audit:
      print("Ejecutando fase de auditoría de calidad de datos...")
      run_audit()
  else:
      print("Saltando fase de auditoría de calidad de datos...")

  print("Pipeline completado!")


if __name__ == "__main__":
    run_pipeline()





