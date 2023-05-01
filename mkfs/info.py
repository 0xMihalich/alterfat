from struct import pack

def sizes(size: int) -> (int, str):
    '''size implementation'''
    
    _sizes = {0: 'B', 10: 'KB', 20: 'MB', 30: 'GB', 40: 'TB'}
    for factor, item in _sizes.items():
        if (size // (1 << factor)) < 1024:
            return factor, item


def fs_info(fs: str, volume_label: str, volume_id: int, free_clusters: int, boot_cluster: int, fsinfo: dict) -> str:
    '''partition info'''
    
    clusters = fsinfo['clusters']
    cluster_size = fsinfo['cluster_size']
    required_size = fsinfo['required_size']

    factor, item = sizes(required_size)
    
    return f'File System:    {fs}\n'\
           f'Volume ID:      {"-".join(pack("<I", volume_id).hex()[i*4:(i+1)*4] for i in range(2))}\n'\
           f'Volume Label:   {volume_label}\n'\
           f'Total Clusters: {clusters}\n'\
           f'Cluster Size:   {cluster_size / 1024 :.01f} KB\n'\
           f'Free Space:     {(free_clusters * boot_cluster) / (1 << factor) :.02f} {item}\n'\
           f'Partition Size: {required_size / (1 << factor) :.02f} {item}'
