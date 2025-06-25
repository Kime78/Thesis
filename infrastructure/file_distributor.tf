terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = ">= 1.0.0"
    }
  }
}

provider "openstack" {
  cloud = "openstack"
}

data "openstack_networking_network_v2" "licenta_net" {
  name = "licenta"
}

resource "openstack_networking_port_v2" "file_distributor_port" {
  name           = "file_distributor_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"
}

resource "openstack_networking_floatingip_v2" "file_distributor_fip" {
  pool = "public"
}

resource "openstack_compute_instance_v2" "file_distributor" {
  name        = "file_distributor"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.file_distributor_port.id
  }
}

resource "openstack_networking_floatingip_associate_v2" "file_distributor_assoc" {
  floating_ip = openstack_networking_floatingip_v2.file_distributor_fip.address
  port_id     = openstack_networking_port_v2.file_distributor_port.id
}

output "file_distributor_floating_ip" {
  description = "Floating IP of the file_distributor instance"
  value       = openstack_networking_floatingip_v2.file_distributor_fip.address
}
