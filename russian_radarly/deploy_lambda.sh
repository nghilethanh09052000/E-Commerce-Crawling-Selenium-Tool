cd russian_radarly/

# Export required variables, as contained in the Russian Radarly project .env file
set -o allexport && source .env && set +o allexport

# Set the Sentry sample rate to 1 in production
export SAMPLE_RATE=1.0
export SENTRY_RELEASE=russian_radarly_$(date +%Y-%m-%d_%H:%M)

# Configure the AWS project (aws configure) if not done yet

# Set the AWS_PAGER variable to null to prevent the CLI to require a user input (Enter/q)
export AWS_PAGER=

# Create a Python virtual environment if not already existing
python3.9 -m venv venv

# Activate it
source venv/bin/activate

# Install the requirements
pip install -r requirements.txt

aws lambda update-function-configuration --function-name russian-radarly-proxy --runtime python3.9 \
--environment "Variables={API_TOKEN=$API_TOKEN,DB_HOST=$DB_HOST,DB_PORT=$DB_PORT,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD,SENTRY_DSN=$SENTRY_DSN,SENTRY_SAMPLE_RATE=$SENTRY_SAMPLE_RATE,SENTRY_RELEASE=$SENTRY_RELEASE}"

# To make the pyscopg2 library (PostgreSQL database adapter) work in Lambda, a simple pip install does not work
# The following solution requires to set the correct runtime version in Lambda (Python 3.9)
# It was retrieved from the following Github repo: https://github.com/jkehler/awslambda-psycopg2.git
# We then put the custom psycopg2 at the root of the russian_radarly repo to override the psycopg2 from the Python venv
# (cp -r awslambda-psycopg2/psycopg2-3.9/ ./psycopg2)

# We call rm with the --force option in order for the command not to fail if the file does not exist
rm --force function.zip

zip -r function.zip lambda_function.py rr_settings.py controller/ database/ enumerator/ psycopg2/ validator/ exception/

# Zip the libraries from the virtual environment at the root of the zipped file
cd venv/lib/python3.9/site-packages/ && zip -r9 ../../../../function.zip . && cd -

aws lambda update-function-code --function-name russian-radarly-proxy --zip-file fileb://function.zip

cd ..
