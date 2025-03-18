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
                    # Remove any existing JMeter results
                    rm -f jmeter_results/results.jtl

                    # Run JMeter tests
                    jmeter -n -t tests/jmeter_test_plan.jmx -l jmeter_results/results.jtl -e -o jmeter_results/junit_results
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
            junit '**/jmeter_results/junit_results/test-*.xml' // Use the correct JUnit XML result path
            echo 'JMeter tests passed!'
        }
        failure {
            junit '**/jmeter_results/junit_results/test-*.xml' // Same here for failed tests
            echo 'JMeter tests failed! Check logs for more details.'
        }
    }
}

