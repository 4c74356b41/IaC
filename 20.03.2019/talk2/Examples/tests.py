@pytest.fixture(scope="session")
def inflate_infrastructure(request):
    # this bit defines how to cleanup after tests
    def fin():
        cleanup_string = 'ansible-playbook cleanup.yml --extra-vars="dp={}" > logs/{}.cleanup'.format(
            deploymentPrefix, dp)
        custom_logger.info('Starting cleanup: %s', cleanup_string)
        subprocess_helper(cleanup_string)
        custom_logger.info('Cleanup done')
    request.addfinalizer(fin)

    # this bit runs ansible with your code with specific parameters
    inflation_string = 'ansible-playbook inflation.yml -vvvv --extra-vars="deploymentPrefix={} dp={}'.format(
        deploymentPrefix, dp)
    inflation = subprocess_helper(inflation_string)
    yield deploymentPrefix


@pytest.fixture(scope="session")
def inflate_kubernetes(request, inflate_infrastructure): # notice this fixture depends on the first fixture
    # this bit defines how to cleanup after tests
    def fin():
        custom_logger.info('Staring kubernetes cleanup')
        subprocess_helper('rm ~/.kube/config')
        subprocess_helper('kubectl delete po/debug')
        custom_logger.info('Kubernetes cleanup done')
    request.addfinalizer(fin)

    # this bit creates a pod on kubernetes we are going to do some tests with
    custom_logger.info('Preparing k8s pods|services: %s',
                       inflate_infrastructure)
    subprocess_helper(
        'python/aks_credentials.py -dp {}'.format(inflate_infrastructure))
    subprocess_helper(
        'kubectl run debug --image=busybox:1.28 --restart=Never -- sleep 3600')


@pytest.mark.usefixtures('inflate_infrastructure')
class TestAzure(object): # this tests check if cosmosdb is successfully installed into the resources group
    @pytest.mark.skipif("pytest.param != '-existing-db'")
    def test_cosmosdb_exists(self, inflate_infrastructure):
        try:
            COSMOC_CLI = client_factory('CosmosDB')
            COSMOC_CLI.database_accounts.list_by_resource_group(
                '{}-k8s'.format(inflate_infrastructure)).next()
            pass
        except (CloudError, StopIteration) as db_error:
            traceback.print_exc()
            pytest.fail('cosmos test failed')

@pytest.mark.usefixtures('inflate_kubernetes')
class TestKubernetes(object): # this test check if sample pod we created in fixture is able to resolve kubernetes dns
    def test_internal_dns_works(self):
        result = subprocess_helper(
            'kubectl exec debug -- nslookup kube-dns.kube-system.svc.cluster.local')
        assert result['returncode'] == 0