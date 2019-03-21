## Outline

[Recording of the talk](https://youtu.be/H9k9F81Esmw?t=1475)

This is a talk that could be subdivided into 2 parts:

1. How to organize your IaC solution workflow\lifecycle
2. How to manage your k8s "infrastructure" (gitops)

## Examples

1. build.yaml - example of how to use your own container to run builds\tests for Azure Devops
2. flux.py - example of how to install flux with pulumi (a bit incomplete at the moment, I will update later)
3. pulumi.py - example of how to install AKS with pulumi (version with comments\explanations can be found [here](https://pulumi.io/quickstart/azure/tutorial-azure-kubernetes-service.html))
4. tests.py - example (non working, just a code snippet from actual code) of how fixtures are used in pytest to define dependencies, more on fixtures [here](https://docs.pytest.org/en/latest/fixture.html)
5. tf.json - example of how to use Azure Terraform provider, more information in [official blog post](https://azure.microsoft.com/en-us/blog/introducing-the-azure-terraform-resource-provider/)

## Links

1. [Flux](https://github.com/weaveworks/flux)
2. [Gitops](https://www.weave.works/blog/gitops-operations-by-pull-request)
3. [Fabrikate](https://github.com/Microsoft/fabrikate)
4. [Fabrikate example configuration](https://dev.azure.com/4c74356b41/_git/fabrikate). Istio, EFK, Promethus, Grafana, Kured, Jaeger, Cert-Manager
5. [Fabrikate resulting configuration](https://github.com/4c74356b41/fabrikate-generated)
6. [Fabrikate build pipeline definition](https://dev.azure.com/4c74356b41/_git/fabrikate?path=%2Fazure-pipeline.yml&version=GBmaster)
7. [Bedrock](https://github.com/Microsoft/bedrock) Fabrikate quick start sample with Terraform
8. [Sample Istio fabrikate configuration](https://github.com/4c74356b41/fabrikate-istio)
9. [Pulumi](https://pulumi.io/)