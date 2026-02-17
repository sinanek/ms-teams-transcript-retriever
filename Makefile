SHELL := /bin/bash

.PHONY: init plan deploy destroy outputs

# Target to initialize Terraform
init:
	cd terraform && terraform init

# Target to view the Terraform plan
plan:
	@echo "Loading variables from .env..."
	@sed 's/ *= */=/' .env > .env.tmp
	@set -a; source .env.tmp; set +a; \
	rm .env.tmp; \
	echo "Running terraform plan..."; \
	cd terraform && terraform plan \
	  -var="project_id=$$GOOGLE_CLOUD_PROJECT" \
	  -var="client_id=$$CLIENT_ID" \
	  -var="client_secret=$$CLIENT_SECRET" \
	  -var="tenant_id=$$TENANT_ID" \
	  -var="region=$${GOOGLE_CLOUD_LOCATION:-europe-west1}"

# Target to deploy the infrastructure
deploy:
	@echo "Loading variables from .env..."
	@sed 's/ *= */=/' .env > .env.tmp
	@set -a; source .env.tmp; set +a; \
	rm .env.tmp; \
	echo "Deploying to project: $$GOOGLE_CLOUD_PROJECT"; \
	cd terraform && terraform apply -auto-approve \
	  -var="project_id=$$GOOGLE_CLOUD_PROJECT" \
	  -var="client_id=$$CLIENT_ID" \
	  -var="client_secret=$$CLIENT_SECRET" \
	  -var="tenant_id=$$TENANT_ID" \
	  -var="region=$${GOOGLE_CLOUD_LOCATION:-europe-west1}"

# Target to destroy the infrastructure
destroy:
	@echo "Loading variables from .env..."
	@sed 's/ *= */=/' .env > .env.tmp
	@set -a; source .env.tmp; set +a; \
	rm .env.tmp; \
	echo "WARNING: Destroying infrastructure in project: $$GOOGLE_CLOUD_PROJECT"; \
	cd terraform && terraform destroy -auto-approve \
	  -var="project_id=$$GOOGLE_CLOUD_PROJECT" \
	  -var="client_id=$$CLIENT_ID" \
	  -var="client_secret=$$CLIENT_SECRET" \
	  -var="tenant_id=$$TENANT_ID" \
	  -var="region=$${GOOGLE_CLOUD_LOCATION:-europe-west1}"

# Target to show outputs
outputs:
	cd terraform && terraform output
