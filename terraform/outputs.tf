output "vm_external_ip" {
  description = "Static external IP of the VM"
  value       = google_compute_address.default.address
}

output "ssh_command" {
  description = "Ready-to-use SSH command"
  value       = "ssh ${var.ssh_user}@${google_compute_address.default.address}"
}
