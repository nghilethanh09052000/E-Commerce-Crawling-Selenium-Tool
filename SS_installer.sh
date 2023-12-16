#! /bin/bash  
  
# This is the basic bash script to install all requirements for SS and setup postgresql DB

# Download pyenv prerequisites
sudo apt install libedit-dev

# Download Pyenv
echo "Downloading Pyenv"
curl https://pyenv.run | bash

# Add to PATH
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Install required Python version and set it as global
pyenv install 3.8.15
pyenv global 3.8.15

# Check Python Version
python_version=$(python --version)
version_num=${python_version:7:1}

if [ "$version_num" == "3" ];
then 
	echo "Python version verified"

	# Create Virtual Environment
	echo "Creating Python virtual environment"
	python -m venv SSenv
	
	#Activate Virtual Environment
	echo "Activating Virtual Environment"
	source ./SSenv/bin/activate

	# Add git submodules
	echo "Adding git Submodules"
	sudo apt-get install git-lfs
	git lfs install
	git submodule init
	git submodule update --init --recursive

	submodules=$(git submodule status)
	echo "$submodules"

	# Check Submodules
	if [[ "$submodules" == *"automated_moderation"* ]];
	then
		echo "Submodule automated_moderation exists"
	else
		echo -e "\n\033[1;31mSubmodule automated moderation not found. Contact Admin\a\033[0m\n"
		# Fall back code here
	fi

	if [[ "$submodules" == *"russian_radarly"* ]];
	then
		echo "Submodule russian_radarly exists"
	else
		echo "\n\033[1;31mSubmodule russian_radarly not found. Contact Admin\a\033[0m\n"
		# Fall back code here
	fi

	if [[ "$submodules" == *"terraform-modules"* ]];
	then
		echo "Submodule terraform-modules exists"
	else
		echo "\n\033[1;31mSubmodule terraform-modules not found. Contact Admin\a\033[0m\n"
		# Fall back code here
	fi

	if [[ "$submodules" == *"_packages/navee_logging"* ]];
	then
		echo "Submodule _packages/navee_logging exists"
	else
		echo "\n\033[1;37mSubmodule _packages/navee_logging not found. Installing with pip\a\033[0m\n"
		pip3 install _packages/navee_logging --upgrade
	fi

	if [[ "$submodules" == *"_packages/navee_utils"* ]];
	then
		echo "Submodule _packages/navee_utils exists"
	else
		echo "\n\033[1;37mSubmodule _packages/navee_utils not found. Installing with pip\a\033[0m\n"
		pip3 install _packages/navee_utils --upgrade
	fi

	if [[ "$submodules" == *"eb_infex_worker"* ]];
	then
		echo "Submodule eb_infex_worker exists"
	else
		echo "\n\033[1;31mSubmodule eb_infex_worker not found. Contact Admin\a\033[0m\n"

	fi

	# Install Requirements
	requirements_path=./deployment/requirements.txt
	automated_moderation_requirements_path=./automated_moderation/deployment/requirements.txt
	eb_infex_worker_requirements_path=./eb_infex_worker/information_extraction/requirements.txt

	echo -e "\n\033[1;42mInstalling Requirements. You might be required to interact with prompts during the installation process. Please take necessary action when prompted.\033[0m\n"
	
	# pip install psycopg2-binary
	
	sudo apt install libpq-dev python3-dev
	sudo apt-get install build-essential
	sudo apt install xvfb

	pip install wheel
	pip install -r $requirements_path
	pip install -r $automated_moderation_requirements_path
	pip install -r $eb_infex_worker_requirements_path

	git pull --recurse-submodules

	pip install pre-commit
	pre-commit install

	echo "Requirements Installed"
	echo " Installing Postgresql"

	# Install Postgresql
	sudo apt update
	sudo apt install postgresql

	echo "Installed all requirements and DB"

	psql_active=$(sudo systemctl is-active postgresql)
	echo "PSQL IS-ACTIVE: $psql_active"

	echo "Creating postgres User and Database"
	sudo -u postgres bash -c "psql -c \"CREATE USER naveeqa WITH PASSWORD 'qwerty';\""
	sudo -u postgres bash -c "psql -c \"CREATE DATABASE naveedb;\""
	sudo -u postgres bash -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE naveedb to naveeqa;\""

	# Rename example env to development.
	mv env.example .env.development
else
	echo "Please install Python 3"
fi

