pipeline {
    agent any

    environment {
        ENV_FILE = "/var/lib/jenkins/env_files/microservices.env"
        WORKSPACE_DIR = "/home/jenkins/workspace/Microservices_Lab_9"
    }

    stages {
        stage('Checkout Code') {
            steps {
                script {
                    checkout scm
                }
            }
        }
        stage('Check Workspace Path') {
            steps {
                script {
                    sh 'echo "Workspace Path: $WORKSPACE"'
                }
            }
        }

        stage('Load Environment Variables') {
            steps {
                script {
                    sh '''
                    if [ -f $ENV_FILE ]; then
                        export $(grep -v '^#' $ENV_FILE | xargs)
                    else
                        echo "⚠️ Warning: .env file not found at $ENV_FILE"
                    fi
                    '''
                }
            }
        }

        stage('Build and Deploy Services') {
            steps {
                script {
                    sh '''
                    docker-compose down
                    docker-compose --env-file /var/lib/jenkins/env_files/microservices.env up -d --build
                    '''
                }
            }
        }

        

        stage('Post-Test Cleanup') {
            steps {
                script {
                    sh '''
                    docker-compose logs > ${WORKSPACE_DIR}/logs/docker-compose.log
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'logs/docker-compose.log'
        }
        
    }
}

