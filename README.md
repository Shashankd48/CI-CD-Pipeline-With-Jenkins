# Production-Grade Automated CI/CD Pipeline for Flask Application

> **Project Submission**: Automated Multi-Stage CI/CD Pipeline with Pytest Gating, Containerization, ECR Artifact Registry, EC2 Automated Deployment, Health Verification, and Email Notification System.

---

## 📌 Executive Summary

This project implements an end-to-end Automated CI/CD Pipeline for a Python Flask Application with MongoDB integration. The pipeline automates the complete cycle from code push on GitHub to production deployment on Amazon EC2 via Amazon Elastic Container Registry (ECR).

```
+--------------+      +-------------------+      +------------------+
| GitHub Repo  | ---> | Jenkins Pipeline  | ---> | PyTest Unit Test |
| (push event) |      | (EC2 / Local)     |      | (Automated Gate) |
+--------------+      +-------------------+      +------------------+
                                                        |
                                                        v Pass
+------------------+      +-------------------+      +------------------+
| Deployment Gate  | <--- |   AWS EC2 Deploy  | <--- | Amazon ECR Push  |
|  (/health check) |      | (Docker Container)|      | (Multi-Stage Img)|
+------------------+      +-------------------+      +------------------+
        |
        v
+------------------+
| HTML Email Notif |
| (Build Status)   |
+------------------+
```

---

## 🏗️ Architecture & Component Overview

1. **Flask Application (`app.py`)**: Web application exposing student management endpoints, connectable to MongoDB (Atlas or self-hosted) via `MONGO_URI`, and a `/health` endpoint for post-deployment verification.
2. **Pytest Suite (`test_app.py`)**: Unit and integration test gate executing on an isolated test database (`TEST_MONGO_URI`).
3. **Multi-Stage Dockerfile (`Dockerfile`)**: Optimized multi-stage Docker build producing a minimal production container image without build-time dependencies.
4. **Amazon ECR**: Container registry storing versioned container images tagged with the Git Commit SHA (`${GIT_COMMIT}`).
5. **Amazon EC2**: Ubuntu 22.04 LTS instance hosting Jenkins and executing deployed application containers.
6. **Jenkins Declarative Pipeline (`Jenkinsfile`)**: 8-stage automated workflow with secured credentials and automated notifications.

---

## 🔑 AWS IAM Policies (Exact JSON Configuration)

### 1. EC2 Instance IAM Role Policy (`EC2-ECR-ReadOnly-Policy`)
Attached to the EC2 instance hosting the application to allow pulling Docker images from Amazon ECR without embedding credentials.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        }
    ]
}
```

### 2. Jenkins IAM User Policy (`Jenkins-ECR-PowerUser-Policy`)
Attached to `jenkins-ecr-user` to grant Jenkins build nodes access to authenticate and push built images to Amazon ECR.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:GetRepositoryPolicy",
                "ecr:DescribeRepositories",
                "ecr:ListImages",
                "ecr:DescribeImages",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## 🚀 Pipeline Stages Breakdown

The CI/CD pipeline is defined in [Jenkinsfile](file:///d:/Study/HeroVired/assignments/CI%20CD%20Pipeline%20Assignment/Jenkinsfile) across 8 distinct stages:

### Stage 1: Checkout
- Clones the latest commit from the GitHub `main` branch.
- Captures Git Commit SHA (`IMAGE_TAG`) for image tagging and tracebility.

### Stage 2: Install Dependencies
- Provisions Python virtual environment (`venv`) and installs `requirements.txt`.

### Stage 3: Test Gate
- Executes `pytest test_app.py`.
- **Quality Gate**: Pipeline aborts immediately if any test fails, blocking image build and deployment.

### Stage 4: Build Multi-Stage Docker Image
- Compiles the application into a 2-stage Docker container (`builder` -> `runner`).
- Tags image with `675789571925.dkr.ecr.ap-south-1.amazonaws.com/flask-student-app:${env.IMAGE_TAG}` and `latest`.

### Stage 5: Push to ECR
- Authenticates against Amazon ECR via AWS CLI.
- Pushes the versioned container image to ECR.

### Stage 6: Deploy to EC2
- Connects to the target EC2 instance via `sshUserPrivateKey` (`ec2-ssh-key`).
- Pulls the newly built image from ECR.
- Stops and removes the old container instance.
- Spawns the new container passing `MONGO_URI` and `SECRET_KEY` from Jenkins Credentials.

### Stage 7: Deploy Verification Gate
- Sends HTTP Requests to `http://${EC2_HOST}:5000/health`.
- Verifies `200 OK` status and active database connectivity before declaring success.

### Stage 8: Post Notification
- Sends a styled HTML email notification (Success / Failure) containing Git SHA, build duration, and logs.

---

## 🔐 Credentials Management Table

All sensitive environment variables and credentials are stored securely using Jenkins Credentials Manager:

| Credential ID | Type | Configured Value / Description |
| :--- | :--- | :--- |
| `aws-credentials` | Username with Password | Access Key: `AKIAZ2WBSQ5K3L4E447S` / Secret: `17Dy+JhThk...` |
| `ec2-ssh-key` | SSH Username with Private Key | Username `ubuntu` with `jenkins-key.pem` Private Key |
| `aws-account-id` | Secret Text | `675789571925` |
| `aws-region` | Secret Text | `ap-south-1` |
| `ecr-repo-name` | Secret Text | `flask-student-app` |
| `ec2-public-ip` | Secret Text | EC2 Public IP address (e.g. `13.x.x.x`) |
| `ec2-username` | Secret Text | `ubuntu` |
| `notify-email` | Secret Text | `jfriday464@gmail.com` |
| `mongo-uri` | Secret Text | MongoDB Atlas (`mongodb+srv://jfriday464_db_user:...@student-app.9lsiu8w.mongodb.net/...`) |
| `flask-secret-key` | Secret Text | Flask session secret key |

> **Note on Credentials Scope**:
> - **SCM Credential (`- none -`)**: Because the GitHub repository is public, the Pipeline Job configuration keeps the SCM credentials set to `- none -`.
> - **Build & Deploy Secrets**: All AWS keys, SSH keys, database URIs, and email notifications are stored in Jenkins Global Credentials Store and referenced in `Jenkinsfile` at runtime.


## 📸 Deliverable Evidence & Screenshots

### 1. AWS IAM Role Configuration
![AWS IAM Role](screenshots/01_aws_iam_role.png)
*Figure 1: IAM Role `EC2-ECR-ReadOnly-Role` with `EC2-ECR-ReadOnly-Policy` attached.*

---

### 2. AWS Security Group Rules
![AWS Security Group](screenshots/02_aws_security_group.png)
*Figure 2: Security Group `flask-jenkins-sg` allowing inbound access on Ports 22, 8080, and 5000.*

---

### 3. EC2 Instance Running
![EC2 Instance](screenshots/03_ec2_instance.png)
*Figure 3: EC2 Instance `Jenkins-Flask-Server` active in AWS Console.*

---

### 4. Jenkins Credentials Store
![Jenkins Credentials](screenshots/04_jenkins_credentials.png)
*Figure 4: Secured credentials registered in Jenkins Credentials Manager.*

---

### 5. GitHub Webhook Integration
![GitHub Webhook](screenshots/05_github_webhook.png)
*Figure 5: Active GitHub Webhook sending push event payloads to Jenkins.*

---

### 6. Amazon ECR Container Images
![Amazon ECR Repository](screenshots/06_ecr_repository.png)
*Figure 6: Amazon ECR repository showing Docker images tagged with Git Commit SHAs.*

---

### 7. Jenkins Pipeline Execution (Success)
![Jenkins Pipeline Success](screenshots/07_pipeline_success.png)
*Figure 7: Successful 8-stage pipeline run in Jenkins Stage View.*

---

### 8. Pipeline Success Email Notification
![Success Email Notification](screenshots/08_email_success.png)
*Figure 8: Automated HTML email notification generated upon successful deployment.*

---

### 9. Test Gate Failure Pipeline Stop
![Jenkins Pipeline Failure](screenshots/09_pipeline_failure.png)
*Figure 9: Pipeline execution gracefully halted at Stage 3 due to a failing test.*

---

### 10. Pipeline Failure Email Notification
![Failure Email Notification](screenshots/10_email_failure.png)
*Figure 10: Automated alert email delivered following test failure.*

---

### 11. EC2 Live Container Verification
![EC2 Docker PS](screenshots/11_ec2_docker_ps.png)
*Figure 11: Active `flask-app` container running on EC2 verified via `docker ps`.*

---

## 🧪 Local Test Verification

To run unit tests locally without modifying application data:

```bash
python -m pytest test_app.py
```

Expected Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Study\HeroVired\assignments\CI CD Pipeline Assignment
collected 5 items

test_app.py .....                                                        [100%]

============================== 5 passed in 0.57s ==============================
```

---

## 📄 License & Maintainer
- **Project**: CI/CD Pipeline Assignment
- **Maintainer**: DevOps Engineering Student
