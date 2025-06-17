#!/bin/bash

# ==============================================================================
# SSH Key Distribution Script
#
# Description:
# This script reads a hosts file (in a format similar to /etc/hosts),
# extracts all hostnames or FQDNs from each line, and then uses
# ssh-copy-id to copy a specified SSH public key to each host.
#
# Usage:
#   ./copy_keys.sh <path_to_hosts_file> <path_to_identity_file>
#
# Example:
#   ./copy_keys.sh ./my_hosts terraform.pem
#
# The hosts file should be formatted like:
#   # Comments are ignored
#   192.168.1.100   web-server-01.example.com web-server-01
#   192.168.1.101   db-server-01.example.com db-server-01
#
# ==============================================================================

# --- Configuration ---
# The username to connect to on the remote hosts.
REMOTE_USER="ubuntu"

# --- Script Validation ---

# Check if the correct number of arguments was provided.
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <path_to_hosts_file> <path_to_identity_file>"
    exit 1
fi

HOSTS_FILE="$1"
IDENTITY_FILE="$2"

# Check if the hosts file exists and is readable.
if [ ! -f "$HOSTS_FILE" ]; then
    echo "Error: Hosts file not found at '$HOSTS_FILE'"
    exit 1
fi

# Check if the identity file exists and is readable.
if [ ! -f "$IDENTITY_FILE" ]; then
    echo "Error: Identity file not found at '$IDENTITY_FILE'"
    exit 1
fi


# --- Main Logic ---

echo "Starting SSH key distribution..."
echo "Hosts File: $HOSTS_FILE"
echo "Identity File: $IDENTITY_FILE"
echo "Remote User: $REMOTE_USER"
echo "========================================"

# Read the hosts file line by line.
# The `|| [[ -n "$line" ]]` part ensures that the loop runs even if the
# last line of the file doesn't end with a newline.
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines or lines that start with a '#' (comments).
    if [[ -z "$line" ]] || [[ "$line" =~ ^\s*# ]]; then
        continue
    fi

    # Read the line into an array of words. The first word is the IP,
    # and the rest are hostnames.
    read -r -a host_entries <<< "$line"

    # We don't need the IP, so we iterate through the array starting from
    # the second element (index 1).
    for (( i=1; i<${#host_entries[@]}; i++ )); do
        hostname="${host_entries[$i]}"
        echo -e "\n--- Processing host: $hostname ---"

        # Attempt to copy the SSH key.
        # -o StrictHostKeyChecking=no : Automatically adds new host keys to known_hosts.
        # -o IdentityFile             : Specifies which private key to use for authentication.
        if ssh-copy-id -f -o StrictHostKeyChecking=no -o IdentityFile="$IDENTITY_FILE" "${REMOTE_USER}@${hostname}"; then
            echo "SUCCESS: Key successfully copied to ${REMOTE_USER}@${hostname}"
        else
            echo "ERROR: Failed to copy key to ${REMOTE_USER}@${hostname}. Check connection or permissions."
        fi
    done

done < "$HOSTS_FILE"

echo -e "\n========================================"
echo "Script finished."

