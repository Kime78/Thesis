terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = ">= 1.49.0"
    }
  }
}

provider "openstack" {
  cloud = "openstack"
}

variable "public_key_file" {
  description = "Path to the public key file to be used for the instances."
  default     = "~/.ssh/id_rsa.pub"
}

resource "openstack_compute_keypair_v2" "terraform_key" {
  name       = "terraform-key"
  public_key = file(var.public_key_file)
}

data "openstack_networking_network_v2" "licenta_net" {
  name = "licenta"
}

locals {
  instance_names = [
    "file_distributor",
    "file_receiver",
    "file_receiver2",
    "file_receiver3",
    "frontend",
    "load_balancer",
    "test",
    "file_downloader",
    "kafka",
    "zookeeper",
    "postgres",
    "storage_node_1",
    "storage_node_2",
    "storage_node_3",
    "storage_node_4",
  ]
}

resource "openstack_networking_port_v2" "ports" {
  count          = length(local.instance_names)
  name           = "${local.instance_names[count.index]}_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"
}

resource "openstack_networking_floatingip_v2" "fips" {
  count = length(local.instance_names)
  pool  = "public"
}

resource "openstack_compute_instance_v2" "instances" {
  count       = length(local.instance_names)
  name        = local.instance_names[count.index]
  image_name  = "Ubuntu Focal"
  flavor_name = contains(["kafka", "zookeeper"], local.instance_names[count.index]) ? "m1.medium" : "m1.small"
  key_pair    = openstack_compute_keypair_v2.terraform_key.name

  network {
    port = openstack_networking_port_v2.ports[count.index].id
  }
}

resource "openstack_networking_floatingip_associate_v2" "fip_assocs" {
  count       = length(local.instance_names)
  floating_ip = openstack_networking_floatingip_v2.fips[count.index].address
  port_id     = openstack_networking_port_v2.ports[count.index].id
}

output "instance_floating_ips" {
  description = "Floating IPs of all instances"
  value = {
    for i in range(length(local.instance_names)) :
    local.instance_names[i] => openstack_networking_floatingip_v2.fips[i].address
  }
}