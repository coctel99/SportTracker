variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "app_name" {
  description = "Used as a prefix for all GCP resource names (VM, IP, firewall)"
  type        = string
  default     = "sport-tracker"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-b"
}

variable "machine_type" {
  description = "Compute Engine machine type (e2-micro is Always Free)"
  type        = string
  default     = "e2-micro"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB (30 GB is within the Always Free tier)"
  type        = number
  default     = 10
}

variable "ssh_user" {
  description = "Linux user on the VM"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "Your personal public SSH key for direct VM access"
  type        = string
}

variable "deploy_public_key" {
  description = "Public SSH key used by GitHub Actions to deploy"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo HTTPS URL"
  type        = string
}

variable "app_dir" {
  description = "Absolute path on the VM where the app will live"
  type        = string
  default     = "/home/ubuntu/sport-tracker"
}

variable "app_secret_key" {
  description = "SPORT_TRACKER_SECRET_KEY written into the server .env"
  type        = string
  sensitive   = true
}
