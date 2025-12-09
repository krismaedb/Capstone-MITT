import sys
import os

PROJECT_PATH = '/var/www/healthclinic'
VENV_PATH = '/var/www/healthclinic/venv'

sys.path.insert(0, PROJECT_PATH)

# Point mod_wsgi to the virtualenv
os.environ['PATH'] = VENV_PATH + '/bin:' + os.environ.get('PATH', '')
os.environ['VIRTUAL_ENV'] = VENV_PATH

# Load your real Flask app
from app import create_app
application = create_app()

