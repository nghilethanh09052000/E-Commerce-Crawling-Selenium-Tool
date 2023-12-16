#!/bin/bash

SAMPLE_RATE=1.0

####################################################
#script function to set properties file value by key
####################################################
setProperty(){
  awk -v pat="^$1=" -v value="$1=$2" '{ if ($0 ~ pat) print value; else print $0; }' $3 > $3.tmp
  mv $3.tmp $3
}
### usage: setProperty $key $value $filename
####################################################

RELEASE=specific_scraper_$(date +%Y-%m-%d-%H:%M)

setProperty "SENTRY_RELEASE" "$RELEASE" ".env.production"

# Prevent Radarly initialization
setProperty "RADARLY_CLIENT_ID" "" ".env.production"

# Build image
aws ecr get-login-password --profile ss --region eu-west-1 | docker login --username AWS --password-stdin 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-lambda-production

docker build -f lambda_redis/Dockerfile -t 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-lambda-production:latest .

setProperty "RADARLY_CLIENT_ID" "QnVZSLCJincLLjxXpZuftHbBHMCCgZ" ".env.production"

# Push the sever image to the containers registry
docker push 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-lambda-production:latest

# Update lambda image
aws lambda update-function-code --profile ss --region eu-west-1 --function-name redis-interface-lambda --image-uri 068631914562.dkr.ecr.eu-west-1.amazonaws.com/specific-scraper-lambda-production:latest
