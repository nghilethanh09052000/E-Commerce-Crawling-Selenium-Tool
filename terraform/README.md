# Terraform documentation

## Setup

Download & install terraform: https://www.terraform.io/downloads

Setup terraform credetials in ~/.aws/credentials (you can find the file's content at https://gitlab.com/navee.ai/scrapping/specific-scraper-v2/-/settings/ci_cd - TF_AWS_CREDENTIALS)

From terraform/ folder, execute the following command:
```
terraform init
```

Create secrets.tfvars file in terraform/ folder (you can find the files content at https://gitlab.com/navee.ai/scrapping/specific-scraper-v2/-/settings/ci_cd - TF_SECRETS)


## Run

To apply terraform changes, go to terraform/ folder and execute the following command:
```
terraform apply -var-file="secrets.tfvars"
```
