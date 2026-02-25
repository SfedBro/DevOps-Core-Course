provider "github" {
  token = var.TF_VAR_GITHUB_TOKEN  # используем переменную TF_VAR
  owner = "SfedBro"        # твой GitHub username или организация
}

resource "github_repository" "course_repo" {
  name        = "DevOps-Core-Course"
  description = "Course repository managed by Terraform"
  private     = false
  has_issues  = true
  has_wiki    = true
}
