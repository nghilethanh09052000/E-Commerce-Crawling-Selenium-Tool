#!/bin/bash

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
cd -

# Make sure that terraform-modules are up to date
cd terraform-modules
git fetch
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
  echo "Terraform modules are not on the branch main."
  exit 1
elif [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
  echo "Terraform modules are not up to date. Please run 'git pull --recurse-submodules' before deploying."
  exit 1
fi
cd -

# Make sure that navee_logging is up to date
cd _packages/navee_logging
git fetch
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
  echo "navee_logging is not on the branch main."
  exit 1
elif [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
  echo "navee_logging is not up to date. Please run 'git pull --recurse-submodules' and 'pip install _packages/navee_logging/ --upgrade' before deploying."
  exit 1
fi
cd -

# Make sure that navee_logging is up to date
cd _packages/navee_utils
git fetch
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
  echo "navee_utils is not on the branch main."
  exit 1
elif [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
  echo "navee_utils is not up to date. Please run 'git pull --recurse-submodules' and 'pip install _packages/navee_utils/ --upgrade' before deploying."
  exit 1
fi
cd -

# Make sure that automated_moderation is up to date
cd automated_moderation
git fetch
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
  echo "automated_moderation is not on the branch main."
  exit 1
elif [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
  echo "automated_moderation is not up to date. Please run 'git pull --recurse-submodules' before deploying."
  exit 1
fi
cd -

# Make sure that eb_infex_worker is up to date
cd eb_infex_worker
git fetch
if [ "$(git rev-parse --abbrev-ref HEAD)" != "master" ]; then
  echo "eb_infex_worker is not on the branch master."
  exit 1
elif [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
  echo "eb_infex_worker is not up to date. Please run 'git pull --recurse-submodules' before deploying."
  exit 1
fi
cd -
