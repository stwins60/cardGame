pipeline {

    agent any

    environment {
        IMAGE_NAME = "idrisniyi94/cardgame"
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {
        stage("Build Docker Image") {
            steps {
                script {
                    sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                }
            }
        }
        stage("Scan Docker Image") {
            steps {
                script {
                    sh "trivy image ${IMAGE_NAME}:${IMAGE_TAG} --format html --output trivy-report.html"
                }
            }
        }
        stage("Publish Trivy Scanned Image Report") {
            steps    {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'trivy-report.html',
                    reportName: 'Trivy Scanned Image Vulnerability Report'
                ])
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
        stage("Scan Kubernetes Configuration files") {
            steps {
                script {
                    sh "trivy config ./k8s --format html --output kubernetes-trivy-report.html"
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