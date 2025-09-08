# ZFS Optimization for ZenGlow Development

## Your Drive Setup

- **60-100GB ext4** (`/`) - System, OS, packages
- **16GB swap** - Memory management
- **1.8TB ZFS** (`/data`) - Development data, Docker volumes

## ZFS Configuration for Development

### 1. ZFS Pool Information

```bash
# Check ZFS pool status
zpool status

# Check available space
zfs list

# Pool properties
zpool get all
```

### 2. Recommended ZFS Datasets

```bash
# Create development datasets
sudo zfs create data/docker           # Docker containers and images
sudo zfs create data/zenglow          # ZenGlow project data
sudo zfs create data/zenglow/cache    # Build caches
sudo zfs create data/zenglow/volumes  # Database volumes
sudo zfs create data/zenglow/backups  # Backup storage

# Set compression for faster I/O
sudo zfs set compression=lz4 data/docker
sudo zfs set compression=lz4 data/zenglow

# Optimize for development workloads
sudo zfs set recordsize=64K data/docker    # Good for container layers
sudo zfs set recordsize=128K data/zenglow  # Good for large files
```

### 3. Docker on ZFS Optimization

```bash
# Configure Docker daemon for ZFS
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "data-root": "/data/docker",
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "features": {
        "buildkit": true
    }
}
EOF

sudo systemctl restart docker
```

### 4. Supabase Volume Configuration

```bash
# Create Supabase data directories on ZFS
mkdir -p /data/zenglow/volumes/postgres
mkdir -p /data/zenglow/volumes/supabase

# Update Supabase config to use ZFS storage
# In supabase/config.toml, add volume mounts
```

### 5. Performance Monitoring

```bash
# Monitor ZFS performance
zpool iostat 1

# Check compression ratios
zfs get compressratio data/docker
zfs get compressratio data/zenglow

# Monitor space usage
watch 'zfs list -o name,used,avail,refer,mountpoint'
```

## Storage Layout Recommendations

### Optimal Directory Structure

```
/ (ext4 - 60-100GB)
├── /boot                    # Boot files
├── /usr                     # System packages
├── /var                     # System logs (keep small)
└── /home                    # User home (minimal)

/data (ZFS - 1.8TB)
├── docker/                  # Docker data root
│   ├── containers/
│   ├── images/
│   └── volumes/
├── zenglow/                 # ZenGlow development
│   ├── cache/              # Build caches
│   ├── volumes/            # Database volumes
│   ├── backups/            # Project backups
│   └── logs/               # Development logs
└── projects/               # Other development projects
```

### Space Allocation Strategy

- **System (ext4)**: 40-60GB used, keep 20-40GB free
- **ZFS Data**: Use compression, expect 1.5-2x effective capacity
- **Docker**: ~200-500GB for images and containers
- **Databases**: ~50-100GB for development data
- **Remaining**: Available for projects and backups

## Performance Tips

### ZFS Tuning for Development

```bash
# Increase ARC (cache) size if you have RAM
echo 'options zfs zfs_arc_max=8589934592' >> /etc/modprobe.d/zfs.conf  # 8GB

# Disable atime for better performance
sudo zfs set atime=off data

# Use faster sync for development (less safe, but faster)
sudo zfs set sync=disabled data/zenglow  # Only for development!
```

### Docker Performance

```bash
# Clean up Docker regularly
alias docker-cleanup='docker system prune -f && docker volume prune -f'

# Monitor Docker space usage
docker system df

# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
```

### Development Workflow

1. **Code** on Windows (fast NVMe/SSD)
2. **Build/Run** in WSL on ZFS (plenty of space)
3. **Database** on ZFS volumes (persistent, backed up)
4. **Cache** on ZFS (compressed, fast access)

## Backup Strategy

### ZFS Snapshots

```bash
# Create snapshot before major changes
sudo zfs snapshot data/zenglow@$(date +%Y%m%d_%H%M%S)

# List snapshots
zfs list -t snapshot

# Rollback if needed
sudo zfs rollback data/zenglow@snapshot_name

# Automated daily snapshots
sudo crontab -e
# Add: 0 2 * * * /usr/sbin/zfs snapshot data/zenglow@daily_$(date +\%Y\%m\%d)
```

### Project Backups

```bash
# Backup ZenGlow project
rsync -av /mnt/c/Users/CGBowen/Documents/GitHub/ZenGlow/ /data/zenglow/backups/windows_sync/

# Backup database
pg_dump -h localhost -p 54322 -U postgres postgres > /data/zenglow/backups/postgres_$(date +%Y%m%d).sql
```

## Monitoring Commands

```bash
# Check overall system health
zg-df                    # Disk usage
zpool status             # ZFS health
docker system df         # Docker space usage
free -h                  # Memory usage

# Performance monitoring
iostat 1                 # I/O statistics
zpool iostat 1          # ZFS I/O
htop                     # CPU/Memory
```

This setup gives you:

- **Fast development** with plenty of space
- **Reliable storage** with ZFS checksums and snapshots
- **Efficient compression** saving 20-40% space
- **Easy backups** with ZFS snapshots
- **Scalable** for future projects
