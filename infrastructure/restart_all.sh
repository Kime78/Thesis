ansible-playbook -i inventory.ini -u ubuntu restart_dist.yml && \
ansible-playbook -i inventory.ini -u ubuntu restart_down.yml && \
ansible-playbook -i inventory.ini -u ubuntu restart_recv.yml && \ 
ansible-playbook -i inventory.ini -u ubuntu restart_nodes.yml