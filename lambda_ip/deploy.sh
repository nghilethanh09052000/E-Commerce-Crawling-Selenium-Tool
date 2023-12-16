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

# Build image
aws ecr get-login-password --profile ss --region eu-west-1 | docker login --username AWS --password-stdin 068631914562.dkr.ecr.eu-west-1.amazonaws.com/get-ip-lambda-production

docker build -f lambda_ip/Dockerfile -t 068631914562.dkr.ecr.eu-west-1.amazonaws.com/get-ip-lambda-production:latest .

# Push the sever image to the containers registry
docker push 068631914562.dkr.ecr.eu-west-1.amazonaws.com/get-ip-lambda-production:latest

# Update lambda image
aws lambda update-function-code --profile ss --region eu-west-1 --function-name ip-lambda --image-uri 068631914562.dkr.ecr.eu-west-1.amazonaws.com/get-ip-lambda-production:latest
