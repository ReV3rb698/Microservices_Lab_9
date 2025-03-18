pipeline {
    agent any

    environment {
        ENV_FILE = "/var/lib/jenkins/env_files/microservices.env"
    }

    stages {
        stage('Checkout Code') {
            steps {
                script {
                    checkout scm
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
                    docker-compose up -d --build
                    '''
                }
            }
        }

        stage('Run JMeter Tests') {
            steps {
                script {
                    sh '''
                    jmeter -n -t tests/jmeter_test_plan.jmx -l jmeter_results/results.jtl
                    '''
                }
            }
        }

        stage('Post-Test Cleanup') {
            steps {
                script {
                    sh '''
                    docker-compose logs > logs/docker-compose.log
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'logs/docker-compose.log'
            archiveArtifacts artifacts: 'jmeter_results/results.jtl'
        }
        success {
            // Parse JMeter results and mark build as successful if no failures
            junit '**/jmeter_results/results.jtl'
            echo 'JMeter tests passed!'
        }
        failure {
            // Parse JMeter results and mark build as failed if there are any failures
            junit '**/jmeter_results/results.jtl'
            echo 'JMeter tests failed! Check logs for more details.'
        }
    }
}

