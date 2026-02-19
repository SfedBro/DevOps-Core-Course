variable "cloud_id" {
  type = string
}

variable "folder_id" {
  type = string
}

variable "zone" {
  type    = string
  default = "ru-central1-a"
}

variable "subnet_id" {
  type = string
}

variable "yc_key_file" {
  description = "Path to Yandex.Cloud service account key"
  type        = string
}

variable "ssh_key" {
  type = string
}
