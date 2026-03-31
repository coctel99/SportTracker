terraform {
  required_version = ">= 1.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Terraform state is stored in a GCS bucket so the team (and CI) share it.
  # Create the bucket once manually (see README) then uncomment this block.
  # backend "gcs" {
  #   bucket = "YOUR_PROJECT_ID-tfstate"
  #   prefix = "sport-tracker"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Static external IP ────────────────────────────────────────────────────────
resource "google_compute_address" "default" {
  name   = "${var.app_name}-ip"
  region = var.region
}

# ── Firewall: allow HTTP, HTTPS, SSH ─────────────────────────────────────────
resource "google_compute_firewall" "allow_web" {
  name    = "${var.app_name}-allow-web"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server", "https-server"]
}

# ── VM instance ───────────────────────────────────────────────────────────────
resource "google_compute_instance" "default" {
  name         = "${var.app_name}-vm-micro"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["http-server", "https-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = var.disk_size_gb
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.default.address
    }
  }

  # SSH key injected from variable — no manual key setup needed
  metadata = {
    ssh-keys = "${var.ssh_user}:${var.ssh_public_key}"
  }

  # Runs once on first boot: installs Docker + nginx, clones repo, writes .env
  metadata_startup_script = templatefile("${path.module}/startup.sh.tpl", {
    ssh_user          = var.ssh_user
    github_repo       = var.github_repo
    app_dir           = var.app_dir
    secret_key        = var.app_secret_key
    deploy_public_key = var.deploy_public_key
  })

  service_account {
    scopes = ["cloud-platform"]
  }
}


