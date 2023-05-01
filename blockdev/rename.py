def rename(name: str) -> str:
    for dev in ('Unknown', 'SCSI', 'ATAPI', 'ATA', '1394', 'SSA', 'Fibre Channel', 'USB',
                'RAID', 'ISCSI', 'SAS', 'SATA', 'SD', 'MMC', 'MAX', 'File Backed Virtual',
                'Storage Spaces', 'NVMe', 'SCM', 'UFS', 'reserved'):
        if dev in name:
            return name.split(dev)[0].strip()
