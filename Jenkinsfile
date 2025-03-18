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
                    rm -f jmeter_results/results.jtl
		    rm -rf /home/jenkins/workspace/Microservices_Lab_9/jmeter_results
                    # Create the folder for JUnit results if it doesn't exist
                    mkdir -p jmeter_results/junit_results

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
            junit '**/jmeter_results/junit_results/test-*.xml'  // Make sure this is the correct path to the JUnit results
            echo 'JMeter tests passed!'
        }
        failure {
            junit '**/jmeter_results/junit_results/test-*.xml'  // Same for failure condition
            echo 'JMeter tests failed! Check logs for more details.'
        }
    }
}

