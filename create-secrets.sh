#!/bin/bash

# This script creates the secrets in Google Cloud Secret Manager
# using the values provided in your .env file.

# Function to load .env file
load_env() {
    if [ -f .env ]; then
        echo "Loading .env file..."
        # Read .env file line by line, remove spaces around =, and export
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            
            # Clean up the line: remove spaces around = and trim quotes if they exist
            # This handles: VAR = "val" -> VAR="val"
            clean_line=$(echo "$line" | sed 's/ *= */=/g')
            
            # Extract key and value
            key=$(echo "$clean_line" | cut -d '=' -f 1)
            value=$(echo "$clean_line" | cut -d '=' -f 2- | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//")
            
            export "$key=$value"
        done < .env
    else
        echo "Error: .env file not found. Please create one based on .env.example."
        exit 1
    fi
}

load_env

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2

    if [ -z "$secret_value" ] || [ "$secret_value" == "CLIENT ID HERE" ] || [ "$secret_value" == "CLIENT SECRET HERE" ] || [ "$secret_value" == "TENANT ID HERE" ]; then
        echo "Warning: Value for $secret_name is not properly set in .env. Skipping..."
        return
    fi

    # Check if secret already exists
    if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
        echo "Secret '$secret_name' already exists. Adding new version..."
        printf "%s" "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
    else
        echo "Creating secret '$secret_name'..."
        printf "%s" "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
    fi
}

# Create the secrets
create_or_update_secret "CLIENT_ID" "$CLIENT_ID"
create_or_update_secret "CLIENT_SECRET" "$CLIENT_SECRET"
create_or_update_secret "TENANT_ID" "$TENANT_ID"

echo "Secret management completed."
