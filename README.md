# Specific Scraper

## Getting started

The Specific Scraper is a project built to enable the scraping of counterfeit content on marketplace and social media domains.

The main project is divided as follows:

### App

  - Configs - The configuration setup for each domain to scrape.
  - DAO - Data Access Layer , all the function calls to the database are done at this level
  - Helpers - utility functions
  - Models - The Database Models
  - Scrapers - The basic interface for the Scraping Function
  - Service - The business logic behind the scraping posts

### Cronjobs

  - The regular scripts we run to launch scraping tasks

### Deployment

  - Deployment Folder

### Scripts

  - Scripts we regularly use

### Tests

  - Scripts to test different elements of the scraper

### Selenium Driver

The selenium driver is separated from the specific scraper business logic. The goal is to eventually move it to a separate package that can be reused cross all platforms. any code written inside selenium driver should be independent from app/


## Installation

1. Clone the Git repo (install git if you already don't have it)

```bash
git clone {{USE GIT LINK HERE}}
```

2. Install Specific Scraper requirements using Bash script

```bash
chmod +x SS_installer.sh
sudo ./SS_installer.sh
```


3. Create new environment (install python 3.8.5 if you don't already have it)

```bash
cd specific-scraper-v2
python -m venv venv
```

4. Access environment

```bash
source ./venv/bin/activate
```

  - Add Git submodules
```bash
git submodule init
git submodule update --init --recursive
```

if you had issues with bidst wheel, install wheel

5. Install requirements (install pip if you don't already have it)

The Scraper Requirements:
  - Step 1:
```bash
pip install -r deployment/requirements.txt
```

if you had errors with psycopg2 try following:
```bash
pip install psycopg2-binary
sudo apt install libpq-dev python3-dev
pip install -r deployment/requirements.txt
```

  - Step 2:
```bash
pip install -r automated_moderation/deployment/requirements.txt
```

  - Step 3:
```bash
pip install -r eb_infex_worker/information_extraction/requirements.txt
```

To run Selenium locally make sure to install chromium driver:
```bash
sudo apt-get install chromium-chromedriver
```

If you don't have Postgresql installed locally you can follow the below tutorial
https://www.tecmint.com/install-postgresql-and-pgadmin-in-ubuntu/

Common Requirements Issues
- Gevent Compiling error [https://stackoverflow.com/questions/26053982/setup-script-exited-with-error-command-x86-64-linux-gnu-gcc-failed-with-exit]
- psycopg2 installation error - [Try installing psycopg2-binary for dev env instead]

6. Git hooks

Git hooks are used to ensure the submodules are always up-to-date

Add the following code to .git/hooks/post-merge:
```
git pull --recurse-submodules
```

7. Pre-commit

Pre-commit are used to ensure the code is well formatted before being pushed to the git repository

Install python pre-commit:
```
pip install pre-commit
```

Setup pre-commit:
```
pre-commit install
```

8. Create .env.development file in specific-scraper-v2 folder with next content:
```
# SENTRY
SAMPLE_RATE_LOGS=1

# AWS
AWS_SUBNETS=None
AWS_GENERAL_SECURITY_GROUP=None
AWS_ROTATING_PROXY_SUBNET=None
AWS_ROTATING_PROXY_SECURITY_GROUP=None
AWS_REGION=eu-west-1

# Database
DB_NAME=scraperdb
DB_HOST=127.0.0.1
DB_USER=postgres
DB_PASSWORD=your_database_password_here
DB_PORT=5432

# Archiving parameters
ARCHIVING_SCROLL_TOLERANCE_THRESHOLD=0
```

9. You can now do your first Test !

*RUN THE SCRAPER*

```bash
export PYTHONPATH=. && export ENVIRONMENT_NAME='development' && python main.py
```
