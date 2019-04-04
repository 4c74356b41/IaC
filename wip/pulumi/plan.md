## sample flow

```python
import xxx

create_aks(name, region, vnet_range, node_size, node_count)
create_aks(name2, region2, vnet_range2, node_size, node_count)

peer_networks(name1, name2)

add_flux_to_k8s(name)
add_flux_to_k8s(name2) # use input to construct label\folder

# alpha\beta.4c74356b41.com
traffic_manager_dns_integration(name1, name2)
```