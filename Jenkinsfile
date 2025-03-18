pipeline {
    agent { label 'bare-metal-agent' } // Change this to match your Jenkins agent label

    environment {
        REPO_URL = 'git@github.com:ReV3rb698/Microservices_Lab_9.git'
        BRANCH = 'main'
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'
    }

    stages {
        stage('Checkout Code') {
            steps {
                script {
                    checkout scm
                }
            }
        }

        stage('Build and Deploy Services') {
            steps {
                script {
                    sh '''
                    docker-compose down
                    docker-compose pull
                    docker-compose up -d
                    '''
                }
            }
        }

        stage('Run JMeter Tests') {
            steps {
                script {
                    sh '''
                    jmeter -n -t tests/jmeter-test.jmx -l results.jtl
                    '''
                }
            }
        }

        stage('Post-Test Cleanup') {
            steps {
                script {
                    sh 'docker-compose logs > logs/docker-compose.log'
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'logs/docker-compose.log'
        }
        failure {
            echo 'Pipeline failed. Check logs for details.'
        }
    }
}
