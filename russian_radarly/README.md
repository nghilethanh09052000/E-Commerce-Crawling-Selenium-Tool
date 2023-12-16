# Russian Radarly

The Russian Radarly project is a proxy to the Instagram scraping solution provided by the Upwork freelancer Eugene Tsaplin.

## Git submodule configuration to add the Russian Radarly submodule to another Git repo

The virtual environment of the Russian Radarly should be created with Python 3.9 (constraint due to the custom package psycopg2 that we need to install).

Install python3.9 in a recent Ubuntu version where only more recent versions of Python are installed:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.9
sudo apt-get install python3.9-venv
```

Create the virtual environment with specifying the version of Python:

```bash
python3.9 -m venv venv
```

```bash
if [ ! -d russian_radarly/ ]; then
  echo "Setting up the Russian Radarly repo"
  git clone git@gitlab.com:navee.ai/scrapping/russian-radarly.git
  mv russian-radarly/ russian_radarly/
  git init russian_radarly
  cd russian_radarly
  python3.9 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
fi

if [ ! -f russian_radarly/.env ]; then
    echo "the .env file must be setup in russian_radarly/"
    exit 1
fi
```

+ setup the .env file in russian_radarly/

### Use psycopg2 (PostgreSQL database adapter) in Lambda

To make the pyscopg2 library (PostgreSQL database adapter) work in Lambda, a simple pip install does not work.
The following solution requires to set the correct runtime version in Lambda (Python 3.9).
It was retrieved from the following Github repo: https://github.com/jkehler/awslambda-psycopg2.git
We then put the custom psycopg2 at the root of the russian_radarly repo to override the psycopg2 from the Python venv
(cp -r awslambda-psycopg2/psycopg2-3.9/ ./psycopg2)

### Common Errors during initialization

If an error related to missing region is shown when running the specific scraper, add: `region_name=AWS_REGION` to the `lambda_client` initialization in `lambda_interface.py`

## Deployment (serverless AWS Lambda)

### Deployment method

We need to update this Lambda function by uploading a compressed file because "The deployment package of your Lambda function "upload_coty_images" is too large to enable inline code editing".

Reference: https://docs.aws.amazon.com/lambda/latest/dg/python-package.html

### Prerequisites

Install Python 3.9 and pip on your laptop. Instructions for Ubuntu (https://askubuntu.com/a/1318849):

```
sudo apt update

sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa

sudo apt update
sudo apt install python3.9
sudo apt install python3.9-venv
```

Configure the AWS project (aws configure sso) if not done yet.

### Deployment command

```
./russian_radarly/deploy_lambda.sh
```
