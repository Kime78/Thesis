ansible-playbook -i inventory.ini -u ubuntu setup_vms.yml && \
ansible-playbook -i inventory.ini -u ubuntu setup_kafka.yml && \
ansible-playbook -i inventory.ini -u ubuntu setup_zookeper.yml && \
ansible-playbook -i inventory.ini -u ubuntu setup_postgres.yml && \
ansible-playbook -i inventory.ini -u ubuntu deploy_file_distributors.yml && \
ansible-playbook -i inventory.ini -u ubuntu deploy_file_downloader.yml && \
ansible-playbook -i inventory.ini -u ubuntu deploy_file_receivers.yml && \
ansible-playbook -i inventory.ini -u ubuntu deploy_load_balancer.yml && \
ansible-playbook -i inventory.ini -u ubuntu deploy_storage_nodes.yml && 
ansible-playbook -i inventory.ini -u ubuntu deploy_frontend.yml