terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
      version = "~> 0.187.0"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  service_account_key_file = var.yc_key_file
  cloud_id                 = var.cloud_id
  folder_id                = var.folder_id
  zone                     = var.zone
}

resource "yandex_compute_instance" "vm-1" {
  name = "terraform-vm"

  resources {
    cores         = 2
    memory        = 1
    core_fraction = 20
  }


  boot_disk {
    initialize_params {
      image_id = "fd8v7ru46kt3s4o5f0uo"
    }
  }

  network_interface {
    subnet_id = var.subnet_id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.ssh_key)}"
  }
}

resource "yandex_vpc_security_group" "vm-sg" {
  name       = "terraform-sg"
  network_id = "enp7tav0a2330i6uh850"

  ingress {
    protocol       = "TCP"
    description    = "SSH"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 22
  }

  ingress {
    protocol       = "TCP"
    description    = "HTTP"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 80
  }

  ingress {
    protocol       = "TCP"
    description    = "App port"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 5000
  }

  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}