import base64
import json
import pulumi
from pulumi import ResourceOptions
from pulumi_azure.core import ResourceGroup
from pulumi_azure.role import Assignment
from pulumi_azure.ad import Application, ServicePrincipal, ServicePrincipalPassword
from pulumi_azure.containerservice import KubernetesCluster, Registry
from pulumi_azure.network import VirtualNetwork, Subnet

from pulumi_kubernetes import Provider
from pulumi_kubernetes.core.v1 import Secret, Namespace, ServiceAccount, ConfigMap
from pulumi_kubernetes.rbac.v1 import ClusterRoleBinding, ClusterRole

from helpers import normalize_name, get_kv_secret, gen_application, PREFIX, PASSWORD, SSHKEY, LOCATION, NAMESPACE

## create_aks()
# create Azure AD Application for AKS
app = Application(
    'aks-app',
    name=PREFIX + '-aks-app'
)

# create service principal for the application so AKS can act on behalf of the application
sp = ServicePrincipal(
    'aks-sp',
    application_id=app.application_id
)

# create service principal password
sppwd = ServicePrincipalPassword(
    'aks-sp-pwd',
    service_principal_id=sp.id,
    end_date='2025-01-01T01:02:03Z',
    value=PASSWORD
)

rg = ResourceGroup(
    'rg',
    name=PREFIX + '-rg',
    location=LOCATION
)

vnet = VirtualNetwork(
    'vnet',
    name=PREFIX + '-vnet',
    location=rg.location,
    resource_group_name=rg.name,
    address_spaces=['10.0.0.0/8']
)

subnet = Subnet(
    'subnet',
    name=PREFIX + '-subnet',
    resource_group_name=rg.name,
    address_prefix='10.0.0.0/23',
    virtual_network_name=vnet.name
)

# create Azure Container Registry to store images in
acr = Registry(
    'acr',
    name=normalize_name(PREFIX + 'acr'),
    location=rg.location,
    resource_group_name=rg.name,
    sku="basic"
)

# assignments are needed for AKS to be able to interact with those resources
acr_assignment = Assignment(
    'acr-permissions',
    principal_id=sp.id,
    role_definition_name='AcrPull',
    scope=acr.id
)

# assignments are needed for AKS to be able to interact with those resources
# acr_assignment = Assignment(
#     'acr-permissions',
#     principal_id=sp.id,
#     role_definition_name='AcrPull',
#     scope="xxx"
# )

subnet_assignment = Assignment(
    'subnet-permissions',
    principal_id=sp.id,
    role_definition_name='Network Contributor',
    scope=subnet.id
)

aks = KubernetesCluster(
    'aks',
    name=PREFIX + '-aks',
    location=rg.location,
    resource_group_name=rg.name,
    kubernetes_version="1.12.6",
    dns_prefix="dns",
    agent_pool_profile=(
        {
            "name": "type1",
            "count": 4,
            "vmSize": "Standard_B2ms",
            "osType": "Linux",
            "maxPods": 110,
            "vnet_subnet_id": subnet.id
        }
    ),
    linux_profile=(
        {
            "adminUsername": "azureuser",
            "ssh_key": [
                {
                    "keyData": SSHKEY
                }
            ]
        }
    ),
    service_principal={
        "clientId": app.application_id,
        "clientSecret": sppwd.value
    },
    role_based_access_control={
        "enabled": "true"
    },
    network_profile=(
        {
            "networkPlugin": "azure",
            "serviceCidr": "10.10.0.0/16",
            "dns_service_ip": "10.10.0.10",
            "dockerBridgeCidr": "172.17.0.1/16"
        }
    ), __opts__=ResourceOptions(depends_on=[acr_assignment, subnet_assignment])
)
## create_aks() ends
k8s = Provider("app_provider", kubeconfig=aks.kube_config_raw, namespace=NAMESPACE)

## add_flux_to_k8s()
Namespace('namespace-flux',
    metadata={
        "name": NAMESPACE
    },
    __opts__=ResourceOptions(
                provider=k8s)
)

ServiceAccount(
    "flux-rbac-sa",
    metadata={
        "name": "flux-rbac-sa",
        "namespace": NAMESPACE
    },
    __opts__=ResourceOptions(
                provider=k8s)
)

ClusterRoleBinding(
    "flux-rbac-crb",
    metadata={
        "name": "flux-rbac-crb",
        "namespace": NAMESPACE
    },
    role_ref={
        "apiGroup": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": "flux-rbac-cr"
    },
    subjects=[
        {
            "kind": "ServiceAccount",
            "name": "flux-rbac-sa",
            "namespace": NAMESPACE
        }
    ],
    __opts__=ResourceOptions(
                provider=k8s)
)

ClusterRole(
    "flux-rbac-cr",
    metadata={
        "name": "flux-rbac-cr",
        "namespace": NAMESPACE
    },
    rules=[
        {
            "apiGroups": [
                "*"
            ],
            "resources": [
                "*"
            ],
            "verbs": [
                "*"
            ]
        },
        {
            "nonResourceURLs": [
                "*"
            ],
            "verbs": [
                "*"
            ]
        }
    ],
    __opts__=ResourceOptions(
                provider=k8s)
)

ConfigMap(
    "flux-configmap",
    metadata={
        "name": "flux-configmap",
        "namespace": NAMESPACE
    },
    data={
        "config": """
apiVersion: v1
clusters: []
contexts:
- context:
    cluster: ""
    namespace: default
    user: ""
  name: default
current-context: default
kind: Config
preferences: {}
users: []
"""
    },
    __opts__=ResourceOptions(provider=k8s)
)

git_key = get_kv_secret('ssh-key')
flux_secret = Secret('flux-secret',
    metadata={
        "name": 'flux-ssh',
        "namespace": NAMESPACE
    },
    data={
        "identity": git_key
    },
    __opts__=ResourceOptions(provider=k8s)
)

## this bit configures cert-manager\external dns
dns_secret = get_kv_secret('client-secret')
azure_json = {
    "tenantId": "www",
    "subscriptionId": "zzz",
    "resourceGroup": "yyy",
    "aadClientId": "xxx",
    "aadClientSecret": dns_secret
}
azure_json_base64 = base64.b64encode(json.dumps(azure_json).encode())
temporary_value = base64.b64encode(dns_secret.encode())

Secret('dns-secret',
    metadata={
        "name": 'azuredns-config',
        "namespace": 'kube-system'
    },
    data={
        "CLIENT-SECRET": temporary_value.decode(),
        "azure.json": azure_json_base64.decode()
    },
    __opts__=ResourceOptions(provider=k8s)
)

gen_application("memcached", [ 11211 ], 'memcached:1.4.25', k8s)
gen_application("flux", [ 3030 ], 'quay.io/weaveworks/flux:1.10.1', k8s, dependencies=[flux_secret], serviceAccount="flux-rbac-sa", volumeMounts=True, volumes=True)

## add_flux_to_k8s() ends