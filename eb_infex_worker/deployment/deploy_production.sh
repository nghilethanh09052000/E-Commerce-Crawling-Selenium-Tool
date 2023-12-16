# To use in case of emergency
# Before running this script, make sure you have set up a counterfeit.production AWS profile ('aws configure sso')
# Make sure your .env.production file is set up correctly
# A local deployment will not properly replace the files stored in Git Large Files System (LFS)
# so you need to manually replace them (eb_infex_worker/information_extraction/models/100__vanilla_trained_models/*.pkl)

# Variables
DOCKERFILE_FOLDER=eb_infex_worker/deployment
AWS_APPLICATION_NAME=counterfeit-worker-infex
SENTRY_APPLICATION_NAME=infex
AWS_DOCKER_FILE=docker-compose.worker.infex.yml
AWS_REGION=eu-west-1

AWS_REGISTRY=749745849812.dkr.ecr.eu-west-1.amazonaws.com
CI_ENVIRONMENT_SLUG=production
CI_JOB_STARTED_AT=$(date +%Y-%m-%d-%H:%M)

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


# Build
aws ecr get-login-password --region $AWS_REGION --profile counterfeit.production | docker login --username AWS --password-stdin $AWS_REGISTRY/$APPLICATION_NAME:latest
docker build -f $DOCKERFILE_FOLDER/Dockerfile -t $AWS_REGISTRY/$AWS_APPLICATION_NAME:latest --cache-from $AWS_REGISTRY/$AWS_APPLICATION_NAME:latest --build-arg ENVIRONMENT_NAME=$CI_ENVIRONMENT_SLUG --build-arg APPLICATION_NAME=$SENTRY_APPLICATION_NAME --build-arg SENTRY_RELEASE=$CI_JOB_STARTED_AT .
docker push $AWS_REGISTRY/$AWS_APPLICATION_NAME:latest

# Deploy
aws s3 --profile counterfeit.production cp $DOCKERFILE_FOLDER/$AWS_DOCKER_FILE s3://docker-images-$CI_ENVIRONMENT_SLUG-navee/$AWS_DOCKER_FILE
aws elasticbeanstalk --profile counterfeit.production create-application-version --application-name $AWS_APPLICATION_NAME --version-label $CI_JOB_STARTED_AT --source-bundle S3Bucket="docker-images-$CI_ENVIRONMENT_SLUG-navee",S3Key="$AWS_DOCKER_FILE"
eb init --profile counterfeit.production -p Docker --region $AWS_REGION $AWS_APPLICATION_NAME
eb deploy $AWS_APPLICATION_NAME --profile counterfeit.production --version $CI_JOB_STARTED_AT --timeout 30
