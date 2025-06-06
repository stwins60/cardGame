pipeline {

    agent any

    environment {
        IMAGE_NAME = "idrisniyi94/cardgame"
        IMAGE_TAG = "${BUILD_NUMBER}"
        DOCKERHUB_CREDENTIALS = credentials('ab8f8dd3-42e0-4d7d-87c5-4950c6145d6c')
    }

    stages {
        stage("Docker Login") {
            steps {
                sh "echo $DOCKERHUB_CREDENTIALS_PSW | docker login -u $DOCKERHUB_CREDENTIALS_USR --password-stdin"
                echo "Login Successful"
            }
        }
        stage("Build Docker Image") {
            steps {
                script {
                    sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                }
            }
        }
        stage("Scan Docker Image with Trivy (HTML Report)") {
            steps {
                script {
                    sh '''
                    # Download Trivy HTML template if not present
                    if [ ! -f html.tpl ]; then
                    curl -sSL -o html.tpl https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/html.tpl
                    fi

                    # Run Trivy image scan using the template
                    trivy image ${IMAGE_NAME}:${IMAGE_TAG} \
                    --format template \
                    --template "@./html.tpl" \
                    --output trivy-report.html
                    '''
                }
            }
        }
        stage("Publish Trivy Scanned Image Report") {
            steps    {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.', // var/jenkins_home/cardGame-deployment/
                    reportFiles: 'trivy-report.html', // var/jenkins_home/cardGame-deployment/trivy-report.html
                    reportName: 'Trivy Scanned Image Vulnerability Report'
                ])
            }
        }
        stage("Docker Push") {
            steps {
                script {
                    def imageName = "${IMAGE_NAME}:${IMAGE_TAG}"
                    sh "docker push ${imageName}"
                }
            }
        }
        stage("Update Deployment with latest image") {
            steps {
                script {
                    sh """
                    sed -i 's|image:.*|image: ${IMAGE_NAME}:${IMAGE_TAG}|' k8s/deployment.yaml
                    """
                }
            }
        }
        stage("Scan Kubernetes Configuration Files with Trivy") {
            steps {
                script {
                    sh '''
                    # Download Trivy HTML template if not present
                    if [ ! -f html.tpl ]; then
                    curl -sSL -o html.tpl https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/html.tpl
                    fi

                    # Run Trivy config scan
                    trivy config ./k8s \
                    --format template \
                    --template "@./html.tpl" \
                    --output kubernetes-trivy-report.html
                    '''
                }
            }
        }

        stage("Publish Trivy Scanned Kubernetes Report") {
            steps    {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'kubernetes-trivy-report.html',
                    reportName: 'Trivy Scanned Kubernetes Config Vulnerability Report'
                ])
            }
        }
        stage("Deploy to Kubernetes") {
            steps {
                withCredentials([file(credentialsId: '7e2fc12c-558d-4521-8060-6c51e976793c', variable: 'KUBECONFIG')]) {
                    sh '''
                    echo "Applying deployment"
                    kubectl apply -f k8s/
                    kubectl rollout status deployment/card-game -n lab-server
                    '''
                }
            }
        }
    }
}