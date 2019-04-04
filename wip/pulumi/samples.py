# забрать что-то в ресурс пулюми
#helpers.py
async def get_aks_credentials():
    result = await get_kubernetes_cluster(name=gen_name('aks'),
                                          resource_group_name=gen_name('rg')
                                          )
    return result.kube_config_raw


#__main__.py
import asyncio

k8s = Provider("app_provider",
                kubeconfig=get_aks_credentials(),
                namespace=BRANCH)


# забрать что-то далеееко
# helpers.py
async def create_sql_database_from_existing(sql_server):
    sql_client = client_factory('SqlManagementClient')
    await sql_server.name.apply(lambda name: sql_client.databases.create_or_update(
            gen_name(BRANCH),
            name, # <pulumi.Output.outputs at 0x23463y5h3>
            'TslTest',
            {
                'location': LOCATION,
                'create_mode': 'Copy',
                'sourceDatabaseId': DBID
            }
        )
    )


#__main__.py
import asyncio

sql_server = SqlServer(
    "sql",
    name=resource_name,
    administrator_login="rootilo",
    administrator_login_password="!Q2w3e4r5t6y",
    location=rg.location,
    resource_group_name=rg.name,
    version="12.0"
)

if not pulumi.runtime.is_dry_run():
    asyncio.ensure_future(
        create_sql_database_from_existing(sql_server))