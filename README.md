recipe-api

Recipe API project


sudo docker build .
sudo docker-compose build
# Linting
sudo docker-compose run --rm app sh -c "flake8"

# Testing
sudo docker-compose run --rm app sh -c "python manage.py test"

# Create new project
sudo docker-compose run --rm app sh -c "django-admin startproject app ."

sudo docker-compose up