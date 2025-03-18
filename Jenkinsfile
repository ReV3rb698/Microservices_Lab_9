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
                    rm -f ${WORKSPACE_DIR}/jmeter_results/results.jtl

                    # Create the folder for JUnit results if it doesn't exist
                    mkdir -p ${WORKSPACE_DIR}/jmeter_results/junit_results

                    # Run JMeter tests
                    jmeter -n -t tests/jmeter_test_plan.jmx -l ${WORKSPACE_DIR}/jmeter_results/results.jtl -e -o ${WORKSPACE_DIR}/jmeter_results/junit_results
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
            archiveArtifacts artifacts: '${WORKSPACE_DIR}/logs/docker-compose.log'
            archiveArtifacts artifacts: '${WORKSPACE_DIR}/jmeter_results/results.jtl'
        }
        success {
            junit '${WORKSPACE_DIR}/jmeter_results/junit_results/test-*.xml'
            echo 'JMeter tests passed!'
        }
        failure {
            junit '${WORKSPACE_DIR}/jmeter_results/junit_results/test-*.xml'
            echo 'JMeter tests failed! Check logs for more details.'
        }
    }
}

