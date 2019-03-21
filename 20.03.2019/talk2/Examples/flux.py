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

gen_application("memcached", [ 11211 ], 'memcached:1.4.25', k8s)
gen_application("flux", [ 3030 ], 'quay.io/weaveworks/flux:1.10.1', k8s, dependencies=[flux_secret], serviceAccount="flux-rbac-sa", volumeMounts=True, volumes=True)
