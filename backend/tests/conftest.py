"""
Configuración compartida de pytest para el backend de Pokeoffice.
"""
import sys
import os
from pathlib import Path

# Asegurar que el directorio raíz del backend esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setear variables de entorno mínimas para que los módulos carguen sin credenciales reales
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-placeholder")
os.environ.setdefault("GOOGLE_DRIVE_CREDENTIALS_PATH", "./credentials.json")
