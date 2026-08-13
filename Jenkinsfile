pipeline {
    agent any

    environment {
        AWS_REGION      = credentials('aws-region')
        AWS_ACCOUNT_ID  = credentials('aws-account-id')
        ECR_REPO_NAME   = credentials('ecr-repo-name')
        EC2_HOST        = credentials('ec2-public-ip')
        EC2_USER        = credentials('ec2-username')
        NOTIFY_EMAIL    = credentials('notify-email')
    }


    stages {
        stage('1. Checkout') {
            steps {
                echo 'Checking out source code from GitHub...'
                checkout scm
                script {
                    env.IMAGE_TAG = env.GIT_COMMIT ? env.GIT_COMMIT : 'latest'
                    env.ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
                    echo "Deploying Git Commit SHA: ${env.IMAGE_TAG}"
                    echo "Target ECR Registry: ${env.ECR_REGISTRY}"
                }

            }
        }

        stage('2. Install Dependencies') {
            steps {
                echo 'Installing Python dependencies from requirements.txt...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('3. Test Gate') {
            steps {
                echo 'Running Pytest test suite...'
                withCredentials([string(credentialsId: 'mongo-uri', variable: 'MONGO_URI'), string(credentialsId: 'flask-secret-key', variable: 'SECRET_KEY')]) {
                    sh '''
                        . venv/bin/activate
                        TEST_MONGO_URI="${MONGO_URI}" pytest test_app.py
                    '''
                }
            }
        }

        stage('4. Build Multistage Docker Image') {
            steps {
                echo "Building Multistage Docker image tagged with Git SHA: ${env.IMAGE_TAG}"
                sh '''
                    docker build -t ${ECR_REGISTRY}/${ECR_REPO_NAME}:${env.IMAGE_TAG} .
                '''
            }
        }

        stage('5. Push to Amazon ECR') {
            steps {
                echo 'Authenticating to Amazon ECR and pushing image...'
                withCredentials([usernamePassword(credentialsId: 'aws-credentials', usernameVariable: 'AWS_ACCESS_KEY_ID', passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                    sh '''
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        docker push ${ECR_REGISTRY}/${ECR_REPO_NAME}:${env.IMAGE_TAG}
                    '''
                }
            }
        }

        stage('6. Deploy to EC2') {
            steps {
                echo 'Deploying application and MongoDB LTS container to EC2 instance via SSH...'
                withCredentials([sshUserPrivateKey(credentialsId: 'ec2-ssh-key', keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER')]) {
                    withCredentials([string(credentialsId: 'mongo-uri', variable: 'MONGO_URI'), string(credentialsId: 'flask-secret-key', variable: 'SECRET_KEY')]) {
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ${EC2_USER}@${EC2_HOST} << EOF
                                # 1. Authenticate to Amazon ECR
                                aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

                                # 2. Pull new Flask application image from ECR
                                docker pull ${ECR_REGISTRY}/${ECR_REPO_NAME}:${env.IMAGE_TAG}

                                # 3. Stop and remove existing Flask application container
                                docker stop flask-app || true
                                docker rm flask-app || true

                                # 4. Run new Flask application container passing MONGO_URI environment variable
                                docker run -d \
                                  --name flask-app \
                                  --restart unless-stopped \
                                  -p 5000:5000 \
                                  -e MONGO_URI="${MONGO_URI}" \
                                  -e SECRET_KEY="${SECRET_KEY}" \
                                  ${ECR_REGISTRY}/${ECR_REPO_NAME}:${env.IMAGE_TAG}
EOF
                        '''

                    }
                }
            }
        }

        stage('7. Deploy Verification Gate') {
            steps {
                echo 'Verifying application health status on EC2...'
                sh '''
                    sleep 5
                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${EC2_HOST}:5000/health)
                    echo "Health check HTTP status: ${STATUS}"
                    if [ "$STATUS" -ne 200 ]; then
                        echo "Deployment verification gate failed! Response code was not HTTP 200."
                        exit 1
                    fi
                    echo "Deployment verification gate passed!"
                '''
            }
        }
    }

    post {
        success {
            emailext (
                to: "${NOTIFY_EMAIL}",
                subject: "✅ [SUCCESS] Jenkins CI/CD Pipeline - Job '${env.JOB_NAME}' #${env.BUILD_NUMBER}",
                body: """
                    <h2>🎉 Pipeline Succeeded!</h2>
                    <p>The Jenkins CI/CD pipeline completed successfully and deployed to Amazon EC2.</p>
                    <ul>
                        <li><b>Job Name:</b> ${env.JOB_NAME}</li>
                        <li><b>Build Number:</b> #${env.BUILD_NUMBER}</li>
                        <li><b>Git Commit SHA:</b> ${env.GIT_COMMIT}</li>
                        <li><b>Git Branch:</b> ${env.GIT_BRANCH}</li>
                        <li><b>Docker Image Tag:</b> ${env.IMAGE_TAG}</li>
                        <li><b>EC2 Target Host:</b> ${EC2_HOST}</li>
                        <li><b>MongoDB Engine:</b> MongoDB 8.0 LTS (Persistent Volume: mongo-data)</li>
                        <li><b>Deploy Verification Gate:</b> PASSED (HTTP 200 /health)</li>
                    </ul>
                    <p><b>Build Console Logs:</b> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                """,
                mimeType: 'text/html'
            )
        }
        failure {
            emailext (
                to: "${NOTIFY_EMAIL}",
                subject: "❌ [FAILURE] Jenkins CI/CD Pipeline - Job '${env.JOB_NAME}' #${env.BUILD_NUMBER}",
                body: """
                    <h2>🚨 Pipeline Failed!</h2>
                    <p>The Jenkins CI/CD pipeline failed during execution.</p>
                    <ul>
                        <li><b>Job Name:</b> ${env.JOB_NAME}</li>
                        <li><b>Build Number:</b> #${env.BUILD_NUMBER}</li>
                        <li><b>Git Commit SHA:</b> ${env.GIT_COMMIT}</li>
                        <li><b>Git Branch:</b> ${env.GIT_BRANCH}</li>
                        <li><b>Failed Stage:</b> Check console logs for exact failing stage</li>
                    </ul>
                    <p><b>Investigate Console Logs Immediately:</b> <a href="${env.BUILD_URL}console">${env.BUILD_URL}console</a></p>
                """,
                mimeType: 'text/html'
            )
        }
    }
}
