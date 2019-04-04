import os
import re
import secrets
import string

import pulumi
from pulumi import ResourceOptions
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Service

from azure.keyvault import KeyVaultClient, KeyVaultAuthentication, KeyVaultId
from azure.common.credentials import ServicePrincipalCredentials


def normalize_name(name):
    regex = re.compile('[^a-zA-Z0-9]')
    replaced = regex.sub('', name)
    normalized = replaced[:23] if len(replaced) > 23 else replaced
    return normalized


def _get_kvclient():
    def auth_callback(server, resource, scope):
        credentials = ServicePrincipalCredentials(
            client_id = os.getenv('ARM_CLIENT_ID'),
            secret = os.getenv('ARM_CLIENT_SECRET'),
            tenant = os.getenv('ARM_TENANT_ID'),
            resource = "https://vault.azure.net"
        )
        token = credentials.token
        return token['token_type'], token['access_token']  


    kv_client = KeyVaultClient(KeyVaultAuthentication(auth_callback))
    return kv_client


def get_kv_secret(name):
    kv_client = _get_kvclient()
    secret = kv_client.get_secret("https://placeholder.vault.azure.net/", name, KeyVaultId.version_none).value
    return secret


def _get_password():
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(20))
    return password


config = pulumi.Config('aks')
PREFIX = pulumi.get_stack()
PASSWORD = config.get('password') or _get_password()
SSHKEY = config.get('sshkey') or 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCxinIAIDDCradZPAgX5GzBLv00u4rigOLUbU00E44FrfMTqu5wXiejJ4ycSb1bI+//ZNgaB2UYRbPL7A9OUKY+K4sX5O84Q6DPMjo/90IANHVTLf3xTaSc7hpvXOtIjJTJeiamxClgnTAcR55RV/j9/Wptxa8GGcRmRCcSmJUkx5AZTFI+s8aF0W3aeHHRw7TxNKBuwrX7FDcHyGKvdkFg4OP863Xe5hp5ql1C3XibmCOp1CMPIU2hCmGOy1LGbOf/Pa+QKAdtUSrPNK/jBWvPWo0k02Ii0JtMAdlpVqnJc3czNIp5gEqZCRCGEdkb/kZnJiMRZhmLBYnC8tiMxvZj core@k8s'
LOCATION = config.get('location') or 'westeurope'
NAMESPACE = config.get('namespace') or 'flux'

args_flux = [
    "--ssh-keygen-dir=/var/fluxd/keygen",
    "--k8s-secret-name=flux-ssh",
    "--memcached-hostname=memcached",
    "--memcached-service=",
    "--git-url=git@ssh.dev.azure.com:v3/xxxxxx",
    "--git-branch=master",
    "--git-path=flux/cluster-setup,flux/{}".format(PREFIX),
    "--git-user=Weave Flux",
    "--git-email=support@weave.works",
    "--git-set-author=false",
    "--git-poll-interval=5m",
    "--git-label={}".format(PREFIX),
    "--git-timeout=20s",
    "--sync-interval=5m",
    "--git-ci-skip=false",
    "--registry-exclude-image=*",
    "--registry-poll-interval=5m",
    "--registry-rps=200",
    "--registry-burst=125",
    "--registry-trace=false"
]

args_memcached = ["-m 64","-p 11211","-I 1m"]

volumeMounts_flux = [
    {
        "name": "kubedir",
        "mountPath": "/root/.kubectl"
    },
    {
        "name": "git-key",
        "mountPath": "/etc/fluxd/ssh",
        "readOnly": True
    },
    {
        "name": "git-keygen",
        "mountPath": "/var/fluxd/keygen"
    }
]

volumes_flux = [
    {
        "name": "kubedir",
        "configmap": {
            "name": "flux-configmap"
        }
    },
    {
        "name": "git-key",
        "secret": {
            "secretName": "flux-ssh",
            "defaultMode": 0o400 # has to be in octal
        }
    },
    {
        "name": "git-keygen",
        "emptyDir": {
            "medium": "Memory"
        }
    }
]

def _gen_service(name, ports, custom_provider, dependencies=[], service_type="ClusterIP"):
    ports = [{"port": port, "target_port": port,
              "name": str(port)} for port in ports]

    labels = {
        "app": name,
        "purpose": "flux"
    }

    Service(name,
            metadata={
                "name": name,
                "labels": labels,
                "namespace": NAMESPACE
            },
            spec={
                "ports": ports,
                "selector": labels,
                "type": service_type,
                "sessionAffinity": "ClientIP"
            },
            __opts__=ResourceOptions(
                provider=custom_provider, depends_on=dependencies)
            )


def _gen_deployment(name, ports, image, custom_provider, serviceAccount, args=[], dependencies=[],
                    replicas=1, resources={}, env={}, volumes=[], volume_mounts=[]):

    keys = ['container_port']
    ports = [dict.fromkeys(keys, port) for port in ports]

    labels = {
        "app": name,
        "purpose": "flux"
    }

    container = {
        "name": name,
        "image": image,
        "imagePullPolicy": "Always",
        "resources": resources,
        "ports": ports,
        "args": args,
        "env": [
            {
                "name": "KUBECONFIG",
                "value": "/root/.kubectl/config"
            }
        ],
        "volumeMounts": volume_mounts 
    }

    Deployment(name,
               metadata={
                   "name": name,
                   "labels": labels,
                   "namespace": NAMESPACE
               },
               spec={
                   "selector": {
                       "match_labels": labels
                   },
                   "replicas": replicas,
                   "template": {
                       "metadata": {
                           "labels": labels
                       },
                       "spec": {
                           "containers": [
                               container
                           ],
                           "serviceAccount": serviceAccount,
                           "volumes": volumes
                       }
                   }
               },
               __opts__=ResourceOptions(
                   provider=custom_provider, depends_on=dependencies)
               )

def gen_application(name, ports, image, customProvider, dependencies=[], serviceAccount="default", volumes=False, volumeMounts=False):
    args = globals()["args_{}".format(name)]
    if volumes:
        volumes = globals()["volumes_{}".format(name)]
    else:
        volumes = []
    if volumeMounts:
        volumeMounts = globals()["volumeMounts_{}".format(name)]
    else:
        volumeMounts = []

    _gen_service(name, ports, customProvider)
    _gen_deployment(name, ports, image, customProvider, serviceAccount, args=args, dependencies=dependencies, volumes=volumes, volume_mounts=volumeMounts) 
