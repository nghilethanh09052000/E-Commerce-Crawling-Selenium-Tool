variable "name" {
  description = "Name of the worker."
  type        = string
}

variable "environment_name" {
  description = "Name of the current environment."
  type        = string
}

variable "subnet_id" {
  description = "Id of the worker Subnet."
  type        = string
}

variable "docker_bucket" {
  description = "Source for docker images to use"
  type        = string
  default     = "docker-images-navee-driver"
}

variable "beanstalk_instance_types" {
  description = "EC2 instance type for the backend."
  type        = string
}

variable "beanstalk_profile" {
  description = "The security profile for beanstalk."
  type        = string
}

variable "security_group" {
  description = "The security group ID for beanstalk."
  type        = string
}

variable "instance_volume_size" {
  description = "The EC2 instances root volume size in GB."
  type        = string
  default     = null
}

variable "scaling_adjustment" {
  description = "The number of instances to add/remove when scaling."
  type        = number
}

variable "min_number_of_instances" {
  description = "Minimum number of instances the worker can create."
  type        = number
}

variable "max_number_of_instances" {
  description = "Maximum number of instances the worker can create."
  type        = number
}

variable "sqs_alarm_low_threshold" {
  description = "Number of messages in the worker queue that trigger the scale down alarm."
  type        = number
  default     = 200
}

variable "sqs_alarm_high_threshold" {
  description = "Number of messages in the worker queue that trigger the scale up alarm."
  type        = number
  default     = 500
}

variable "connection_timeout" {
  description = "Time to wait for a request to be processed before timing out."
  type        = number
  default     = 600
}

variable "max_connection" {
  description = "Maximum number of connections."
  type        = number
  default     = 50
}


variable "immutable_deployment" {
  description = "Whether the worker deployment should immutable or not"
  type        = string
  default     = "false"
}