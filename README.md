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

> [!NOTE]
> **Dynamic EC2 Public IP Addresses in Screenshots**: Because the Amazon EC2 instance is hosted on AWS Free Tier without an Elastic IP, stopping and restarting the server assigned new public IPv4 addresses at different implementation phases. As a result, different public IP addresses (e.g. `13.x.x.x`, `3.x.x.x`) appear across screenshots for SSH, Webhooks, and Application URLs, but all correspond to the same underlying EC2 instance.

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
- Captures Git Commit SHA (`IMAGE_TAG`) for image tagging and traceability.

### Stage 2: Install Dependencies
- Provisions Python virtual environment (`venv`) and installs `requirements.txt`.

### Stage 3: Test Gate
- Executes `pytest test_app.py`.
- **Quality Gate**: Pipeline aborts immediately if any test fails, blocking image build and deployment.

### Stage 4: Build Multi-Stage Docker Image
- Compiles the application into a 2-stage Docker container (`builder` -> `runner`).
- Tags image with `${ECR_REGISTRY}/${ECR_REPO_NAME}:${env.IMAGE_TAG}` and `latest`.

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
| `aws-credentials` | Username with Password | AWS Access Key ID & Secret Access Key |
| `ec2-ssh-key` | SSH Username with Private Key | Username `ubuntu` with `.pem` Private Key |
| `aws-account-id` | Secret Text | 12-digit AWS Account ID |
| `aws-region` | Secret Text | AWS Region (e.g. `us-east-1` or `ap-south-1`) |
| `ecr-repo-name` | Secret Text | ECR Repository Name (`flask-student-app`) |
| `ec2-public-ip` | Secret Text | EC2 Public IP address |
| `ec2-username` | Secret Text | `ubuntu` |
| `notify-email` | Secret Text | Recipient Email Address for build notifications |
| `mongo-uri` | Secret Text | Production MongoDB URI (`student_db`) |
| `test-mongo-uri` | Secret Text | Test Suite MongoDB URI (`test_student_db`) |
| `flask-secret-key` | Secret Text | Flask session secret key |

> **Note on Credentials Scope**:
> - **SCM Credential (`- none -`)**: Because the GitHub repository is public, the Pipeline Job configuration keeps the SCM credentials set to `- none -`.
> - **Build & Deploy Secrets**: All AWS keys, SSH keys, database URIs, and email notifications are stored in Jenkins Global Credentials Store and referenced in `Jenkinsfile` at runtime.

---

## 📧 SMTP Email Notification Setup (Gmail SMTP)

To enable HTML email notifications for pipeline builds in Jenkins:

### Step 1: Generate Google App Password
1. Navigate to [Google Account Security Settings](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is turned **ON**.
3. Access [App Passwords](https://myaccount.google.com/apppasswords).
4. Create an App Password named `Jenkins` and copy the 16-character token.

### Step 2: Configure Extended E-mail Notification in Jenkins
1. Go to **Manage Jenkins** → **System**.
2. Under **Jenkins Location**, set **System Admin e-mail address** to your Gmail address.
3. Scroll to **Extended E-mail Notification**:
   - **SMTP server**: `smtp.gmail.com`
   - **SMTP Port**: `465`
   - Under **Advanced**:
     - Next to **Credentials**, click **+ Add** → **Jenkins**.
     - **Kind**: Username with password.
     - **Username**: Your Gmail address (e.g., `user@gmail.com`).
     - **Password**: Paste the 16-character App Password.
     - Check **Use SSL**.
4. Scroll to **E-mail Notification** (standard):
   - **SMTP server**: `smtp.gmail.com`
   - Click **Advanced**:
     - Check **Use SMTP Authentication**.
     - **Username**: Your Gmail address.
     - **Password**: 16-character App Password.
     - Check **Use SSL** and set **SMTP Port** to `465`.
     - Check **Test configuration by sending test e-mail** and verify `Email was sent successfully`.
5. Click **Save**.

---

## 📸 Deliverable Evidence & Screenshots

### 1. AWS IAM Role Configuration
![AWS IAM Role](screenshots/01-created-ecr-ec2-role.png)
*Figure 1: IAM Role `EC2-ECR-ReadOnly-Role` with `EC2-ECR-ReadOnly-Policy` attached.*

---

### 2. AWS IAM User Creation
![AWS IAM User](screenshots/02-created-jenkins-user.png)
*Figure 2: Dedicated IAM User `jenkins-ecr-user` created for Jenkins ECR authentication.*

---

### 3. AWS Security Group Rules
![AWS Security Group](screenshots/03-added-flask-jenkins-sg.png)
*Figure 3: Security Group `flask-jenkins-sg` configured with inbound rules for Ports 22 (SSH), 8080 (Jenkins), and 5000 (Flask App).*

---

### 4. EC2 Instance Launch
![EC2 Instance](screenshots/04-launched-ec2-instance.png)
*Figure 4: Active Ubuntu 22.04 LTS EC2 instance running in AWS Console.*

---

### 5. Automated Server Initialization Script
![Shell Script Setup](screenshots/05-install-kenkins-with-shell-script.png)
*Figure 5: Executing the automated shell script on EC2 to install Docker, Java 21, Python venv, and Jenkins.*

---

### 6. Initial Jenkins Unlock
![Jenkins Initial Password](screenshots/06-jenkins-setup-done-with-admin-password.png)
*Figure 6: Unlocking Jenkins using the initial admin password from `/var/lib/jenkins/secrets/initialAdminPassword`.*

---

### 7. Plugin Installation
![Installing Plugins](screenshots/07-installing-required-plugins-jenkins.png)
*Figure 7: Installing suggested plugins (Git, Pipeline, SSH Agent, Email Extension).*

---

### 8. Creating First Admin User
![Create Admin User](screenshots/08-creating-first-admin-user-jenkins.png)
*Figure 8: Creating the primary administrator user account in Jenkins.*

---

### 9. Jenkins Dashboard Ready
![Jenkins Ready](screenshots/09-jenkins-setup-done-and-ready-to-use.png)
*Figure 9: Jenkins environment successfully initialized and ready for pipeline execution.*

---

### 10. Amazon ECR Repository Creation
![AWS ECR Repo](screenshots/10-created-aws-ecr-repo.png)
*Figure 10: Private Amazon ECR repository `flask-student-app` created in AWS Region `ap-south-1`.*

---

### 11. MongoDB Atlas Setup
![MongoDB Atlas Setup](screenshots/11-setting-up-mongodb-database-on-atlas.png)
*Figure 11: Configuring MongoDB Atlas cloud database for application data storage.*

---

### 12. MongoDB Atlas Cluster & Network Access
![MongoDB Atlas Cluster](screenshots/12-creating-cluster-in-atlas.png)
*Figure 12: Creating MongoDB Atlas cluster and whitelisting IP addresses in Network Access.*

---

### 13. Jenkins Credentials Manager Setup
![Jenkins Credentials](screenshots/13-jenkins-credentials-setup-done.png)
*Figure 13: All 11 sensitive environment variables and credentials registered securely in Jenkins Global Credentials Store.*

---

### 14. GitHub Webhook Configuration
![GitHub Webhook](screenshots/14-setting-up-github-webhook-for-jenkins.png)
*Figure 14: Configuring GitHub Webhook with Payload URL `http://<EC2_IP>:8080/github-webhook/` for automatic push triggers.*

---

### 15. Jenkins Pipeline Job Setup
![Jenkins Pipeline Job](screenshots/15-setting-up-jenkins-pipeline.png)
*Figure 15: Configuring Pipeline Job with `GitHub hook trigger for GITScm polling` pointing to `Jenkinsfile` on branch `*/main`.*

---

### 16. Webhook Delivery Verification
![Webhook Delivery](screenshots/16-github-webhook-delivery-successfull.png)
*Figure 16: GitHub Webhook delivery verification returning HTTP 200 payload response.*

---

### 17. PyTest Quality Gate Enforcement
![PyTest Failure](screenshots/17-initial-test-cases-failing.png)
*Figure 17: Quality Gate demonstration - pipeline execution aborted at Stage 3 due to unit test failure, preventing bad deployment.*

---

### 18. MongoDB Atlas Network IP Restrictions
![Atlas Network Access](screenshots/18-allow-altas-db-only-from-server-ip.png)
*Figure 18: Securing MongoDB Atlas connection rules to restrict access to EC2 server IP.*

---

### 19. Initial Build Success (Email Pending SMTP Config)
![Initial Build Success](screenshots/19-initial-build-success-but email failed.png)
*Figure 19: All 7 core deployment stages passing prior to SMTP configuration.*

---

### 20. SMTP Extended E-mail Configuration
![SMTP Configuration](screenshots/20-smtp-email-configuration.png)
*Figure 20: Configuring Gmail SMTP authentication and SSL credentials in Jenkins Extended E-mail Notification.*

---

### 21. Failure Notification Testing (Pipeline Broken & Email Alert)
![Pipeline Failure Step 1](screenshots/21-intentional-build-failed-pipeline-broken-step-1.png)
*Figure 21a: Intentional broken build triggering stage failure in Jenkins.*

![Failure Email Step 2](screenshots/21-intentional-build-failed-emaiil-received-step-2.png)
*Figure 21b: Automated HTML alert email received in inbox detailing the build failure.*

---

### 22. End-to-End Successful Deployment & Email Verification
![Pipeline Success Stages](screenshots/22-1-all-steps-of-pipeline-successfully-completed.png)
*Figure 22a: Complete 8-stage pipeline run passing in Jenkins Stage View.*

![Success Email Inbox](screenshots/22-2-success-email-received.png)
*Figure 22b: Automated HTML success notification received in Gmail inbox containing build details, Git SHA, and EC2 host.*

![Live Application Verified](screenshots/22-3-finally-successfullyed-deloyed-with-success-email.png)
*Figure 22c: Live Flask application active on EC2 (`http://<EC2_IP>:5000/`) alongside success email confirmation.*

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
