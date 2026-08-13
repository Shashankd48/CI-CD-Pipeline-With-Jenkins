# Complete Step-by-Step Deployment & Configuration Guide

This guide provides the exact step-by-step instructions, JSON IAM policies, commands, and Jenkins configurations needed to set up and deploy the Flask Application using **Jenkins**, **Amazon ECR**, and **Amazon EC2**.

---

## 🛠️ Step 1: AWS IAM Setup (Exact JSON Policies)

### 1.1 Create IAM Role for EC2 (`EC2-ECR-ReadOnly-Role`)
This role is attached to the EC2 instance to allow pulling Docker images from Amazon ECR without embedding AWS credentials on the server.

1. Go to **AWS IAM Console** -> **Roles** -> **Create Role**.
2. Select **AWS Service** -> **EC2** -> Click **Next**.
3. Create Policy with the following **JSON Policy**:

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

4. Name the policy: `EC2-ECR-ReadOnly-Policy`.
5. Attach the policy to the role and name the role: `EC2-ECR-ReadOnly-Role`.

---

### 1.2 Create IAM User for Jenkins (`jenkins-ecr-user`)
This user provides `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` for Jenkins to authenticate and push built Docker images to ECR.

1. Go to **AWS IAM Console** -> **Users** -> **Create User**.
2. Name: `jenkins-ecr-user` -> Click **Next**.
3. Create Policy with the following **JSON Policy**:

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

4. Name the policy: `Jenkins-ECR-PowerUser-Policy`.
5. Attach this policy to `jenkins-ecr-user`.
6. Navigate to `jenkins-ecr-user` -> **Security credentials** tab -> **Create access key** (Command Line Interface CLI).
7. Save the generated **Access Key ID** and **Secret Access Key** securely.

---

## 🌐 Step 2: AWS Security Group Setup (`flask-jenkins-sg`)

1. Go to **EC2 Console** -> **Security Groups** -> **Create Security Group**.
2. Name: `flask-jenkins-sg`.
3. Inbound Rules configuration:

| Type | Protocol | Port Range | Source | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | `22` | `0.0.0.0/0` | Remote SSH management |
| **Custom TCP** | TCP | `8080` | `0.0.0.0/0` | Jenkins Web UI |
| **Custom TCP** | TCP | `5000` | `0.0.0.0/0` | Flask App & `/health` endpoint |

---

## 💻 Step 3: EC2 Instance Provisioning

1. Go to **EC2 Console** -> **Launch Instance**.
2. **Name**: `Jenkins-Flask-Server`.
3. **AMI**: Ubuntu Server 22.04 LTS (64-bit x86).
4. **Instance Type**: `t2.medium` (recommended) or `t3.micro`.
5. **Key Pair**: Select or create `jenkins-key.pem`.
6. **Network Settings**: Select `flask-jenkins-sg`.
7. **Advanced Details**: Set **IAM Instance Profile** to `EC2-ECR-ReadOnly-Role`.
8. Click **Launch Instance** and record the **Public IPv4 Address**.

---

## ⚙️ Step 4: EC2 Server Initialization Script

SSH into your EC2 instance and execute the following commands:

```bash
#!/bin/bash
set -e

echo "=== 1. Updating System & Installing Dependencies ==="
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release fontconfig openjdk-21-jre openjdk-21-jdk awscli python3-venv python3-pip

echo "=== 2. Installing & Enabling Docker ==="
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu

echo "=== 3. Adding Jenkins Official GPG Key & Repository ==="
sudo mkdir -p /usr/share/keyrings
sudo curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

echo "=== 4. Installing Jenkins ==="
sudo apt-get update -y
sudo apt-get install -y jenkins

echo "=== 5. Configuring Jenkins Permissions & Starting Service ==="
sudo usermod -aG docker jenkins
sudo systemctl enable --now jenkins
sudo systemctl restart jenkins

echo "=== 6. Jenkins Setup Complete! ==="
echo "Your initial Jenkins Admin Password is:"
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```


---

## 📦 Step 5: Amazon ECR Repository Creation

1. Go to **AWS ECR Console** -> **Repositories** -> **Create repository**.
2. Visibility: **Private**.
3. Name: `flask-student-app`.
4. Copy the ECR Repository URI (Format: `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/flask-student-app`).

---

## 🚀 Step 6: Jenkins Setup & Credentials Configuration

### 6.1 Plugin Installation
Navigate to **Manage Jenkins** -> **Plugins** -> **Available plugins** and install:
- `Docker Pipeline`
- `SSH Agent`
- `Email Extension` (`email-ext`)

### 6.2 Credentials Configuration Table
Navigate to **Manage Jenkins** -> **Credentials** -> **System** -> **Global credentials (unrestricted)** -> **Add Credentials**:

| # | Credential ID | Kind | Key / Field | Exact Value / Instruction |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `aws-credentials` | Username with password | **Username**<br>**Password** | `<AWS_ACCESS_KEY_ID>`<br>`<AWS_SECRET_ACCESS_KEY>` |
| 2 | `ec2-ssh-key` | SSH Username with private key | **Username**<br>**Private Key** | `ubuntu`<br>Select *Enter directly* -> Paste full contents of your `.pem` key |
| 3 | `aws-account-id` | Secret text | **Secret** | `<YOUR_AWS_ACCOUNT_ID>` *(e.g. 123456789012)* |
| 4 | `aws-region` | Secret text | **Secret** | `ap-south-1` |
| 5 | `ecr-repo-name` | Secret text | **Secret** | `flask-student-app` |
| 6 | `ec2-public-ip` | Secret text | **Secret** | `<YOUR_EC2_PUBLIC_IP>` *(e.g. 13.x.x.x from EC2 Console)* |
| 7 | `ec2-username` | Secret text | **Secret** | `ubuntu` |
| 8 | `notify-email` | Secret text | **Secret** | `<YOUR_EMAIL_ADDRESS>` *(e.g. user@gmail.com)* |
| 9 | `mongo-uri` | Secret text | **Secret** | `mongodb+srv://<username>:<password>@cluster0.mongodb.net/student_db` |
| 10 | `flask-secret-key` | Secret text | **Secret** | `<YOUR_SECRET_KEY>` |

---

## 🔗 Step 7: Configure GitHub Webhook & Jenkins Pipeline Job

### 7.1 GitHub Webhook Setup
1. Open your GitHub Repository -> **Settings** -> **Webhooks** -> Click **Add webhook**.
2. **Payload URL**: `http://<YOUR_EC2_PUBLIC_IP>:8080/github-webhook/`
3. **Content type**: `application/json`
4. **Which events would you like to trigger this webhook?**: Select **Pushes**.
5. Click **Add webhook** (Ensure a green checkmark appears).

### 7.2 Creating the Jenkins Pipeline Job (Step-by-Step)
1. Open Jenkins Dashboard (`http://<YOUR_EC2_PUBLIC_IP>:8080`).
2. Click **New Item** in the left menu bar.
3. Enter an item name: `flask-student-pipeline`.
4. Select **Pipeline** as the item type, then click **OK** at the bottom.
5. In the **General** section, optional: add a description.
6. Scroll down to **Triggers**:
   - Check the box: **GitHub hook trigger for GITScm polling**.
7. Scroll down to **Pipeline**:
   - **Definition**: Select **Pipeline script from SCM**.
   - **SCM**: Select **Git**.
   - **Repository URL**: Enter `https://github.com/Shashankd48/CI-CD-Pipeline-With-Jenkins`
   - **Credentials**: Keep as **`- none -`** *(Since the GitHub repo is public; pipeline secrets for AWS/ECR/EC2/MongoDB are fetched automatically at runtime from Global Credentials)*.
   - **Branches to build / Branch Specifier**: Enter `*/main`.
   - **Script Path**: Enter `Jenkinsfile`.
8. Click **Save** at the bottom.
9. Click **Build Now** on the left menu to trigger your build!



---

## 📸 Step 8: Evidence Screenshot Requirements

Capture the following screenshots and place them in the `screenshots/` directory:

| Filename | Step / Requirement |
| :--- | :--- |
| `01_aws_iam_role.png` | AWS IAM Role `EC2-ECR-ReadOnly-Role` with policy attached |
| `02_aws_security_group.png` | Inbound rules for `flask-jenkins-sg` (Ports 22, 8080, 5000) |
| `03_ec2_instance.png` | Running EC2 Instance in AWS Console |
| `04_jenkins_credentials.png` | Jenkins Global Credentials store list |
| `05_github_webhook.png` | GitHub Webhook configuration with green checkmark |
| `06_ecr_repository.png` | AWS ECR repository showing images tagged with Git Commit SHA |
| `07_pipeline_success.png` | Jenkins Pipeline Stage View showing all 8 stages GREEN |
| `08_email_success.png` | Customized Success Email received in inbox |
| `09_pipeline_failure.png` | Jenkins Pipeline Stage View showing Test Gate Failure (RED) |
| `10_email_failure.png` | Customized Failure Email received in inbox |
| `11_ec2_docker_ps.png` | Terminal output of `docker ps` on EC2 showing running container |
