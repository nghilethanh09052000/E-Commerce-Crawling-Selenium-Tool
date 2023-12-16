#!/bin/bash

SAMPLE_RATE=1.0

RELEASE=scraping_worker_$(date +%Y-%m-%d-%H:%M)

####################################################
#script function to set properties file value by key
####################################################
setProperty(){
  awk -v pat="^$1=" -v value="$1=$2" '{ if ($0 ~ pat) print value; else print $0; }' $3 > $3.tmp
  mv $3.tmp $3
}
### usage: setProperty $key $value $filename
####################################################

setProperty "SENTRY_RELEASE" "$RELEASE" ".env"

# Set the Sentry sample rate to the value specified at the top of this file
setProperty "SAMPLE_RATE_LOGS" "$SAMPLE_RATE" ".env"

if [ ! -d russian_radarly/ ]; then
  echo "Setting up the Russian Radarly repo"
  git clone git@gitlab.com:navee.ai/scrapping/russian-radarly.git
  mv russian-radarly/ russian_radarly/
  git init russian_radarly
  cd russian_radarly
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
fi

if [ ! -f russian_radarly/.env ]; then
    echo "the .env file must be setup in russian_radarly/"
    exit 1
fi

# Make sure that russian-radarly is up to date
cd russian_radarly
git fetch
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
  echo "Russian Radarly is not on the branch main."
  exit 1
elif [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
  echo "Russian Radarly is not up to date. Please run 'git pull --recurse-submodules' before deploying."
  exit 1
fi
cd ..

# Build image
docker build --pull -f deployment/Dockerfile -t 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-production:latest --build-arg SENTRY_RELEASE=$RELEASE .

# Set the Sentry sample rate back to 0 after having built the Docker image
setProperty "SAMPLE_RATE_LOGS" "0" ".env"

# Connect to AWS containers registry
aws ecr get-login-password --profile specificscrapers.production --region eu-west-1 | docker login --username AWS --password-stdin 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-production

# Push the sever image to the containers registry
docker push 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-production

# Deploy
PACKAGE=$RELEASE.zip
cd eb_scraping_worker/deployment && ln docker-compose.worker.yml docker-compose.yml
zip -r $PACKAGE .ebextensions docker-compose.yml && cd -
aws s3 --profile specificscrapers.production cp eb_scraping_worker/deployment/$PACKAGE s3://docker-images-navee-driver/$PACKAGE
aws elasticbeanstalk --profile specificscrapers.production create-application-version --application-name scraping-worker --version-label $RELEASE --source-bundle S3Bucket="docker-images-navee-driver",S3Key="$PACKAGE" --region eu-west-1
aws elasticbeanstalk --profile specificscrapers.production update-environment --application-name scraping-worker --environment-name scraping-worker --version-label $RELEASE --region eu-west-1
