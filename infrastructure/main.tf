terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = ">= 1.0.0"
    }
  }
}

provider "openstack" {
  cloud = "openstack" # Match this with the entry in clouds.yaml
}

# --- Network Configuration ---
# Assuming 'licenta_network_id' is known or can be fetched via a data source
# For simplicity, if 'licenta' is the network name, we'll need its ID.
# If you have the network ID, you can replace data.openstack_networking_network_v2.licenta_net.id with it.
data "openstack_networking_network_v2" "licenta_net" {
  name = "licenta"
}

# --- Port Definitions ---

resource "openstack_networking_port_v2" "file_distributor_port" {
  name           = "file_distributor_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"
}

resource "openstack_networking_port_v2" "file_receiver_port" {
  name           = "file_receiver_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"
}

resource "openstack_networking_port_v2" "kafka_port" {
  name           = "kafka_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"
}

resource "openstack_networking_port_v2" "zookeeper_port" {
  name           = "zookeeper_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "postgres_port" {
  name           = "postgres_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "storage_node_1_port" {
  name           = "storage_node_1_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "storage_node_2_port" {
  name           = "storage_node_2_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "storage_node_3_port" {
  name           = "storage_node_3_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "storage_node_4_port" {
  name           = "storage_node_4_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "storage_node_5_port" {
  name           = "storage_node_5_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

resource "openstack_networking_port_v2" "storage_node_6_port" {
  name           = "storage_node_6_port"
  network_id     = data.openstack_networking_network_v2.licenta_net.id
  admin_state_up = "true"

}

# --- Security Group (Example - ensure 'default' exists or define it) ---
# If your "default" security group is pre-existing and you know its ID, you can remove this
# and directly use the ID in port definitions. Otherwise, this ensures it's managed by Terraform.
# --- Floating IP Definitions ---

resource "openstack_networking_floatingip_v2" "file_distributor_fip" {
  pool = "public" # Change to your external network name
}

resource "openstack_networking_floatingip_v2" "file_receiver_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "kafka_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "zookeeper_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "postgres_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "storage_node_1_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "storage_node_2_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "storage_node_3_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "storage_node_4_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "storage_node_5_fip" {
  pool = "public"
}

resource "openstack_networking_floatingip_v2" "storage_node_6_fip" {
  pool = "public"
}

# --- Instance Definitions ---

resource "openstack_compute_instance_v2" "file_distributor" {
  name        = "file_distributor"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  # security_groups are now managed by the port
  network {
    port = openstack_networking_port_v2.file_distributor_port.id
  }
}

resource "openstack_compute_instance_v2" "file_receiver" {
  name        = "file_receiver"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.file_receiver_port.id
  }
}

resource "openstack_compute_instance_v2" "kafka" {
  name        = "kafka"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.medium"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.kafka_port.id
  }
}

resource "openstack_compute_instance_v2" "zookeeper" {
  name        = "zookeeper"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.medium"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.zookeeper_port.id
  }
}

resource "openstack_compute_instance_v2" "postgres" {
  name        = "postgres"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.postgres_port.id
  }
}

resource "openstack_compute_instance_v2" "storage_node_1" {
  name        = "storage_node_1"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.storage_node_1_port.id
  }
}

resource "openstack_compute_instance_v2" "storage_node_2" {
  name        = "storage_node_2"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.storage_node_2_port.id
  }
}

resource "openstack_compute_instance_v2" "storage_node_3" {
  name        = "storage_node_3"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.storage_node_3_port.id
  }
}

resource "openstack_compute_instance_v2" "storage_node_4" {
  name        = "storage_node_4"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.storage_node_4_port.id
  }
}

resource "openstack_compute_instance_v2" "storage_node_5" {
  name        = "storage_node_5"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.storage_node_5_port.id
  }
}

resource "openstack_compute_instance_v2" "storage_node_6" {
  name        = "storage_node_6"
  image_name  = "Ubuntu Focal"
  flavor_name = "m1.small"
  key_pair    = "terraform"
  network {
    port = openstack_networking_port_v2.storage_node_6_port.id
  }
}

# --- Floating IP Associations ---

resource "openstack_networking_floatingip_associate_v2" "file_distributor_assoc" {
  floating_ip = openstack_networking_floatingip_v2.file_distributor_fip.address
  port_id     = openstack_networking_port_v2.file_distributor_port.id
}

resource "openstack_networking_floatingip_associate_v2" "file_receiver_assoc" {
  floating_ip = openstack_networking_floatingip_v2.file_receiver_fip.address
  port_id     = openstack_networking_port_v2.file_receiver_port.id
}

resource "openstack_networking_floatingip_associate_v2" "kafka_assoc" {
  floating_ip = openstack_networking_floatingip_v2.kafka_fip.address
  port_id     = openstack_networking_port_v2.kafka_port.id
}

resource "openstack_networking_floatingip_associate_v2" "zookeeper_assoc" {
  floating_ip = openstack_networking_floatingip_v2.zookeeper_fip.address
  port_id     = openstack_networking_port_v2.zookeeper_port.id
}

resource "openstack_networking_floatingip_associate_v2" "postgres_assoc" {
  floating_ip = openstack_networking_floatingip_v2.postgres_fip.address
  port_id     = openstack_networking_port_v2.postgres_port.id
}

resource "openstack_networking_floatingip_associate_v2" "storage_node_1_assoc" {
  floating_ip = openstack_networking_floatingip_v2.storage_node_1_fip.address
  port_id     = openstack_networking_port_v2.storage_node_1_port.id
}

resource "openstack_networking_floatingip_associate_v2" "storage_node_2_assoc" {
  floating_ip = openstack_networking_floatingip_v2.storage_node_2_fip.address
  port_id     = openstack_networking_port_v2.storage_node_2_port.id
}

resource "openstack_networking_floatingip_associate_v2" "storage_node_3_assoc" {
  floating_ip = openstack_networking_floatingip_v2.storage_node_3_fip.address
  port_id     = openstack_networking_port_v2.storage_node_3_port.id
}

resource "openstack_networking_floatingip_associate_v2" "storage_node_4_assoc" {
  floating_ip = openstack_networking_floatingip_v2.storage_node_4_fip.address
  port_id     = openstack_networking_port_v2.storage_node_4_port.id
}

resource "openstack_networking_floatingip_associate_v2" "storage_node_5_assoc" {
  floating_ip = openstack_networking_floatingip_v2.storage_node_5_fip.address
  port_id     = openstack_networking_port_v2.storage_node_5_port.id
}

resource "openstack_networking_floatingip_associate_v2" "storage_node_6_assoc" {
  floating_ip = openstack_networking_floatingip_v2.storage_node_6_fip.address
  port_id     = openstack_networking_port_v2.storage_node_6_port.id
}

# --- Outputs for Floating IPs ---
output "file_distributor_floating_ip" {
  description = "Floating IP of the file_distributor instance"
  value       = openstack_networking_floatingip_v2.file_distributor_fip.address
}

output "file_receiver_floating_ip" {
  description = "Floating IP of the file_receiver instance"
  value       = openstack_networking_floatingip_v2.file_receiver_fip.address
}

output "kafka_floating_ip" {
  description = "Floating IP of the kafka instance"
  value       = openstack_networking_floatingip_v2.kafka_fip.address
}

output "zookeeper_floating_ip" {
  description = "Floating IP of the zookeeper instance"
  value       = openstack_networking_floatingip_v2.zookeeper_fip.address
}

output "postgres_floating_ip" {
  description = "Floating IP of the postgres instance"
  value       = openstack_networking_floatingip_v2.postgres_fip.address
}

output "storage_node_1_floating_ip" {
  description = "Floating IP of the storage_node_1 instance"
  value       = openstack_networking_floatingip_v2.storage_node_1_fip.address
}

output "storage_node_2_floating_ip" {
  description = "Floating IP of the storage_node_2 instance"
  value       = openstack_networking_floatingip_v2.storage_node_2_fip.address
}

output "storage_node_3_floating_ip" {
  description = "Floating IP of the storage_node_3 instance"
  value       = openstack_networking_floatingip_v2.storage_node_3_fip.address
}

output "storage_node_4_floating_ip" {
  description = "Floating IP of the storage_node_4 instance"
  value       = openstack_networking_floatingip_v2.storage_node_4_fip.address
}

output "storage_node_5_floating_ip" {
  description = "Floating IP of the storage_node_5 instance"
  value       = openstack_networking_floatingip_v2.storage_node_5_fip.address
}

output "storage_node_6_floating_ip" {
  description = "Floating IP of the storage_node_6 instance"
  value       = openstack_networking_floatingip_v2.storage_node_6_fip.address
}

# ... (add similar outputs for all other floating IPs if needed)
