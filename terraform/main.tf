terraform {
  backend "s3" {
    bucket  = "terraform-state-specific-scraper-navee-bucket"
    key     = "core/terraform.tfstate"
    region  = "eu-west-1"
    profile = "tf.specific-scrapers.production"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "3.73.0"
    }
  }
}

provider "aws" {
  region  = "eu-west-1"
  profile = "tf.specific-scrapers.production"

  default_tags {
    tags = {
      Project = "Specific-Scraper"
      Env     = "Production"
    }
  }
}

module "devops_accounts" {
  source = "../terraform-modules/devops_accounts"
}
