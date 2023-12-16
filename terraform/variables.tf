variable "default_az" {
  description = "Default Availability Zone"
  type        = string
  default     = "eu-west-1a"
}

variable "second_az" {
  description = "Secondary Availability Zone"
  type        = string
  default     = "eu-west-1b"
}

variable "DB_PWD" {
  description = "Database password."
}

variable "connection_timeout" {
  description = "Time to wait for a request to be processed before timing out."
  type        = number
  default     = 600
}

data "aws_elastic_beanstalk_hosted_zone" "current" {}


data "aws_elastic_beanstalk_solution_stack" "docker" {
  most_recent = true
  name_regex  = "^64bit Amazon Linux 2 (.*) running Docker$"
}

variable "instance_volume_size" {
  description = "The EC2 instances root volume size in GB."
  type        = string
  default     = "100"
}

variable "max_number_of_instance" {
  description = "Number of RISE instances"
  type        = number
  default     = 11
}

variable "domain_name" {
  description = "Navee Driver domain name"
  type        = string
  default     = "driver.navee.com"
}
