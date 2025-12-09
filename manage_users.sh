#!/bin/bash
cd /var/www/healthclinic
source venv/bin/activate
python3 app/create_user.py "$@"
