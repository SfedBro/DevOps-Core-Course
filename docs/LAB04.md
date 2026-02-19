# LAB04 — Infrastructure as Code (Terraform & Pulumi)

## 1. Cloud Provider & Infrastructure

### Cloud Provider

Cloud provider: Yandex Cloud

Rationale:

- Free tier available
- Simple interface
- Integrated CLI
- Fast VM provisioning
- Suitable for educational DevOps tasks

### Instance Configuration

- Platform: standard-v1
- CPU: 2 cores
- Memory: 1 GB
- Core fraction: 20 percent
- OS image: Ubuntu 18.04
- NAT enabled
- Security group rules:
  - Port 22 (SSH)
  - Port 80 (HTTP)
  - Port 5000 (App)

Reason:\
Chosen to stay within free tier limits.

### Region / Zone

ru-central1-a

Chosen because it is default region and available in free tier.

### Cost

Total cost: 0 RUB (free tier configuration and new-user grant were used)

### Resources Created

Terraform:

- VPC Security Group
- Security Group Rules
- Compute Instance
- External IP

Pulumi:

- VPC Security Group
- 4 Security Group Rules
- Compute Instance
- External IP

## 2. Terraform Implementation

### Terraform Version

Terraform v1.14.5 (amd64)\
Provider: yandex-cloud/yandex

### Project Structure

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
└── terraform.tfvars
```

- main.tf — infrastructure definition
- variables.tf — variable definitions
- outputs.tf — output values
- terraform.tfvars — variable values
  P.S.:outputs for both implementations are in `OUTPUT.txt`'s corresponding folders.

### Key Configuration Decisions

- Used free tier instance size
- Added security group explicitly
- Enabled NAT for SSH access
- Used SSH key authentication

### Challenges Encountered

SSH key path formatting\
Understanding provider configuration\
Free tier CPU configuration\
Stop of all billing processes(part 1)

### Terraform init Output

```
Initializing the backend...
Initializing provider plugins...
- Reusing previous version of yandex-cloud/yandex from the dependency lock file
- Using previously-installed yandex-cloud/yandex v0.187.0
```

### Terraform plan Output

```
Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + external_ip = (known after apply)
```

### Terraform apply Output

```
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

external_ip = "93.77.184.211"
```

### SSH Connection

`ssh ubuntu@<external_ip>`

```
ssh ubuntu@93.77.184.211
Successfully connected to VM.
```

## 3. Pulumi Implementation

### Pulumi Version & Language

Pulumi v3.221.0\
Language: Python

### Code differs from Terraform

Terraform uses HCL (declarative configuration language).
Pulumi uses Python (imperative programming language).

Terraform describes desired state.
Pulumi uses programming constructs (loops, variables, logic).

### Advantages Discovered

Pulumi:

- More flexible
- Full programming language
- Easier dynamic logic(but not for me, personally)

Terraform:

- Cleaner structure
- More readable for infrastructure
- Simpler configuration
- More stable ecosystem

### Challenges Encountered

- pkg_resources error (setuptools version issue)
- Service account authentication configuration
- Security group syntax differences
- SSH key needed earlier

### pulumi preview Output

```
Outputs:
    external_ip: [unknown]

Resources:
    + 7 to create
```

### pulumi up Output

```
Outputs:
    external_ip: "89.169.159.54"

Resources:
    + 7 to create
```

### SSH Connection

`ssh ubuntu@<external_ip>`

```
ssh ubuntu@89.169.159.54
Successfully connected to VM.
```

## 4. Terraform vs Pulumi Comparison

### Ease of Learning

Terraform was easier to learn because HCL is designed specifically for infrastructure.\
Pulumi required understanding Python SDK structure and <b>provider behavior</b>(the hardest part was to stop the billing completely).

### Code Readability

Terraform configuration is more readable for infrastructure.\
Pulumi mixes infrastructure with programming logic, which can be less clear.

### Debugging

Terraform errors were clearer and easier to understand.\
Pulumi had dependency and SDK version issues which required troubleshooting.

### Documentation

Terraform has broader documentation and more examples.\
Pulumi documentation is good but less mature.

### Use Case

Terraform:

- Best for pure infrastructure provisioning
- Teams managing cloud resources
- Production environments

Pulumi:

- Complex infrastructure with dynamic logic
- When strong programming integration is needed
- Developers comfortable with Python/TypeScript

### Preferred Tool

I prefer <b>Terraform</b>

- Simpler syntax
- Cleaner structure
- Easier to debug
- More predictable workflow
- More windows-users-friendly(In my personal opinion)

## 5. Lab 5 Preparation & Cleanup

VM for Lab 5:

- I destroyed both Terraform and Pulumi VMs. (due to billing, yeah)
- I will recreate VM for Lab 5 when needed. (it is simple, indeed)

### Cleanup Output

`terraform destroy`

```
Destroy complete! Resources: 2 destroyed.
```

`pulumi destroy`

```
Outputs:
  - external_ip: "62.84.119.154"

Resources:
    - 7 deleted

Duration: 44s
```

P.S.: All remaining resources were manually verified in the cloud console and confirmed as deleted.
