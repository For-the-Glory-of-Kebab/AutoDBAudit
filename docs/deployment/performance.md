# Performance Guide

**Audience**: System administrators, database administrators, performance engineers
**Purpose**: Optimize AutoDBAudit performance for large-scale SQL Server environments
**Last Updated**: 2025-12-30

---

## Table of Contents

* [Performance Overview](#performance-overview)
* [System Requirements](#system-requirements)
* [Configuration Tuning](#configuration-tuning)
* [Database Optimization](#database-optimization)
* [Network Optimization](#network-optimization)
* [Parallel Processing](#parallel-processing)
* [Memory Management](#memory-management)
* [Monitoring and Profiling](#monitoring-and-profiling)
* [Troubleshooting Performance](#troubleshooting-performance)
* [Scaling Strategies](#scaling-strategies)

---

## Performance Overview

### Performance Characteristics

AutoDBAudit is designed for **enterprise-scale SQL Server security auditing** with the following performance characteristics:

* **Concurrent Processing**: Parallel audit execution across multiple SQL Server instances
* **Memory Efficient**: Streaming data processing for large datasets
* **Network Optimized**: Intelligent connection pooling and timeout management
* **Storage Efficient**: Compressed data storage with optimized indexing

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Single Server Audit | < 5 minutes | Basic security checks |
| Multi-Server Audit (10 servers) | < 15 minutes | Parallel execution |
| Large Environment (50+ servers) | < 60 minutes | Optimized for scale |
| Memory Usage | < 2GB | For typical workloads |
| Disk Usage | < 500MB per audit | Compressed storage |

### Performance Factors

**System Factors**:
- Hardware specifications (CPU, RAM, storage)
- Network latency and bandwidth
- SQL Server performance and load

**Configuration Factors**:
- Timeout settings
- Parallel processing limits
- Memory allocation

**Environmental Factors**:
- Number of target servers
- Database sizes and complexity
- Network topology

---

## System Requirements

### Minimum Hardware

| Component | Minimum | Recommended | Enterprise |
|-----------|---------|-------------|------------|
| CPU Cores | 2 | 4 | 8+ |
| RAM | 4 GB | 8 GB | 16 GB+ |
| Storage | 500 GB SSD | 1 TB NVMe SSD | 2 TB+ NVMe |
| Network | 100 Mbps | 1 Gbps | 10 Gbps |

### Operating System Tuning

#### Windows Performance Settings

**Power Plan**:
```powershell
# Set to High Performance
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

**Virtual Memory**:
- Initial: 1.5x RAM
- Maximum: 3x RAM
- Place on fast SSD storage

#### Windows Registry Optimizations

**TCP/IP Tuning**:
```
HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters
- MaxUserPort = 65534
- TcpTimedWaitDelay = 30
```

**ODBC Connection Pooling**:
```
HKLM\SOFTWARE\ODBC\ODBCINST.INI\Microsoft ODBC Driver 18 for SQL Server
- CPTimeout = 60
```

### SQL Server Configuration

#### Connection Settings
```sql
-- Optimize for audit connections
EXEC sp_configure 'user connections', 100;
RECONFIGURE;

-- Enable connection pooling
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'remote query timeout', 600;
RECONFIGURE;
```

#### Resource Governor (Optional)
```sql
-- Create resource pool for audit connections
CREATE RESOURCE POOL audit_pool
WITH (
    MIN_CPU_PERCENT = 0,
    MAX_CPU_PERCENT = 20,
    MIN_MEMORY_PERCENT = 0,
    MAX_MEMORY_PERCENT = 20
);

CREATE WORKLOAD GROUP audit_group
USING audit_pool;
```

---

## Configuration Tuning

### Connection Timeouts

**Default Settings**:
```json
{
  "global_settings": {
    "timeout_seconds": 30,
    "connect_timeout": 30,
    "query_timeout": 300
  }
}
```

**Tuning Guidelines**:

| Network Latency | Connect Timeout | Query Timeout |
|----------------|----------------|---------------|
| < 10ms (LAN) | 10 seconds | 60 seconds |
| 10-100ms | 30 seconds | 120 seconds |
| > 100ms (WAN) | 60 seconds | 300 seconds |

### Parallel Processing Configuration

**Default Parallel Settings**:
```json
{
  "parallel_processing": {
    "max_concurrent_servers": 5,
    "max_concurrent_queries": 10,
    "batch_size": 100
  }
}
```

**Scaling Guidelines**:

| Server Count | Max Concurrent | Batch Size |
|-------------|----------------|------------|
| 1-5 | 5 | 100 |
| 6-20 | 10 | 50 |
| 21-50 | 15 | 25 |
| 50+ | 20 | 10 |

### Memory Configuration

**Memory Limits**:
```json
{
  "memory_settings": {
    "max_memory_mb": 1024,
    "stream_threshold_mb": 100,
    "cache_size_mb": 256
  }
}
```

---

## Database Optimization

### SQLite Optimization

**PRAGMA Settings**:
```sql
-- Optimize for audit workload
PRAGMA synchronous = NORMAL;
PRAGMA journal_mode = WAL;
PRAGMA cache_size = 1000000;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
```

**Index Optimization**:
```sql
-- Performance indexes
CREATE INDEX idx_findings_server_status ON findings(server_name, status);
CREATE INDEX idx_audit_history_timestamp ON audit_history(created_at);
CREATE INDEX idx_row_annotations_finding ON row_annotations(finding_uuid);
```

### Query Optimization

**Efficient Query Patterns**:
```sql
-- Use EXISTS instead of COUNT for existence checks
SELECT 1 WHERE EXISTS (SELECT 1 FROM findings WHERE status = 'CRITICAL')

-- Use UNION ALL for combining results
SELECT server_name, 'CRITICAL' as severity FROM critical_findings
UNION ALL
SELECT server_name, 'HIGH' as severity FROM high_findings

-- Use LIMIT for sampling large datasets
SELECT * FROM findings ORDER BY severity DESC LIMIT 1000
```

### Data Archival Strategy

**Automatic Cleanup**:
```sql
-- Archive old audit data
DELETE FROM audit_history WHERE created_at < datetime('now', '-1 year');

-- Vacuum database to reclaim space
VACUUM;
```

---

## Network Optimization

### Connection Pooling

**ODBC Connection String Optimization**:
```
Driver={ODBC Driver 18 for SQL Server};
Server=server_name;
Database=master;
Trusted_Connection=yes;
Connection Timeout=30;
Pooling=yes;
Max Pool Size=10;
Min Pool Size=1;
```

### Network Protocol Selection

**Protocol Priority**:
1. **TCP/IP** (preferred for performance)
2. **Named Pipes** (local connections only)
3. **Shared Memory** (local connections only)

### Firewall Optimization

**Required Ports**:
- SQL Server: 1433 (default), configured ports
- WinRM: 5985 (HTTP), 5986 (HTTPS)
- DNS: 53 (UDP/TCP)

**Firewall Rules**:
```powershell
# Optimize firewall for audit traffic
New-NetFirewallRule -DisplayName "AutoDBAudit SQL" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow -Profile Domain
New-NetFirewallRule -DisplayName "AutoDBAudit WinRM" -Direction Inbound -Protocol TCP -LocalPort 5985,5986 -Action Allow -Profile Domain
```

---

## Parallel Processing

### Threading Model

**Architecture**:
- **Main Thread**: Coordination and UI
- **Worker Threads**: SQL Server connections (IO-bound)
- **Background Threads**: File operations and logging

**Thread Pool Configuration**:
```python
# Optimal thread pool sizes
sql_threads = min(cpu_count() * 2, max_concurrent_servers)
file_threads = cpu_count()
```

### Concurrency Control

**Semaphore Limits**:
```python
# Control concurrent operations
server_semaphore = asyncio.Semaphore(max_concurrent_servers)
query_semaphore = asyncio.Semaphore(max_concurrent_queries)
file_semaphore = asyncio.Semaphore(5)
```

### Load Balancing

**Server Distribution**:
- Group servers by geographic location
- Balance load across network segments
- Prioritize high-priority servers

---

## Memory Management

### Memory Usage Patterns

**Audit Phase**:
- Connection objects: ~1MB per server
- Query results: Variable (streamed)
- Excel processing: ~50MB base + 10MB per 1000 findings

**Sync Phase**:
- Database comparison: ~100MB for large audits
- State tracking: ~50MB
- Excel updates: ~25MB

**Remediation Phase**:
- Script generation: ~10MB
- Execution tracking: ~5MB

### Memory Optimization Techniques

**Streaming Data Processing**:
```python
# Process large result sets in chunks
def process_findings_streaming(cursor, batch_size=1000):
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        process_batch(rows)
        del rows  # Free memory immediately
```

**Object Reuse**:
```python
# Reuse connection objects
connection_pool = {}
def get_connection(server):
    if server not in connection_pool:
        connection_pool[server] = create_connection(server)
    return connection_pool[server]
```

### Garbage Collection Tuning

**GC Configuration**:
```python
import gc

# Aggressive garbage collection for memory-intensive operations
gc.set_threshold(700, 10, 10)
gc.enable()
```

---

## Monitoring and Profiling

### Performance Metrics

**Key Metrics to Monitor**:
- Audit duration per server
- Memory usage over time
- Network latency
- Database query performance
- Thread utilization

### Logging Configuration

**Performance Logging**:
```python
import logging
import time

class PerformanceLogger:
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        logger.info(f"Operation completed in {duration:.2f}s")
```

### Profiling Tools

**Built-in Profiling**:
```bash
# Enable Python profiling
python -m cProfile -s time main.py audit --new > profile.txt

# Memory profiling
python -c "import tracemalloc; tracemalloc.start(); exec(open('main.py').read())"
```

**External Tools**:
- **Process Monitor**: Windows Sysinternals for system calls
- **Performance Monitor**: Windows built-in performance counters
- **SQL Server Profiler**: Database query analysis

---

## Troubleshooting Performance

### Common Performance Issues

#### Slow Audit Execution

**Symptoms**:
- Audit takes > 30 minutes for basic checks
- High CPU usage on client
- Memory usage growing continuously

**Causes & Solutions**:

**Network Latency**:
```bash
# Test network latency
ping target-server

# Adjust timeouts for high-latency networks
# config/sql_targets.json
{
  "connect_timeout": 60,
  "query_timeout": 600
}
```

**SQL Server Performance**:
```sql
-- Check SQL Server performance
SELECT * FROM sys.dm_exec_requests WHERE blocking_session_id <> 0;

-- Optimize audit queries
CREATE INDEX idx_audit_tables ON audit_tables(table_name);
```

#### Memory Issues

**Symptoms**:
- Out of memory errors
- System slowdown
- Application crashes

**Solutions**:
```json
// Reduce memory usage
{
  "memory_settings": {
    "max_memory_mb": 512,
    "stream_threshold_mb": 50,
    "cache_size_mb": 128
  }
}
```

#### Database Bottlenecks

**Symptoms**:
- Slow sync operations
- Large database file growth
- Query timeouts

**Solutions**:
```sql
-- Optimize database performance
PRAGMA optimize;
VACUUM;

-- Check database size
SELECT page_count * page_size as size_bytes FROM pragma_page_count(), pragma_page_size();
```

### Performance Monitoring Queries

**SQL Server Performance**:
```sql
-- Monitor active connections
SELECT
    session_id,
    host_name,
    program_name,
    cpu_time,
    memory_usage
FROM sys.dm_exec_sessions
WHERE program_name LIKE '%autodbaudit%';

-- Check for blocking
SELECT
    blocking_session_id,
    session_id,
    wait_type,
    wait_time
FROM sys.dm_exec_requests
WHERE blocking_session_id <> 0;
```

**Windows Performance**:
```powershell
# Monitor process performance
Get-Process -Name python | Select-Object CPU, Memory, Handles

# Check network connections
Get-NetTCPConnection | Where-Object {$_.RemotePort -eq 1433}
```

---

## Scaling Strategies

### Horizontal Scaling

**Multi-Client Deployment**:
- Deploy AutoDBAudit on multiple client machines
- Divide server inventory across clients
- Aggregate results in central repository

**Load Balancer Integration**:
- Use network load balancers for high availability
- Distribute audit load across multiple clients
- Implement failover mechanisms

### Vertical Scaling

**Hardware Upgrades**:
- Increase CPU cores for parallel processing
- Add RAM for larger datasets
- Use NVMe storage for faster I/O

**Configuration Scaling**:
```json
{
  "enterprise_settings": {
    "max_concurrent_servers": 50,
    "memory_limit_mb": 4096,
    "query_timeout": 1800
  }
}
```

### Cloud Optimization

**Azure SQL Database**:
- Use connection pooling extensively
- Implement retry logic for transient failures
- Optimize for cloud network latency

**AWS RDS SQL Server**:
- Configure appropriate instance sizes
- Use Multi-AZ for high availability
- Implement connection multiplexing

### Large Environment Strategies

#### Batch Processing
```python
# Process servers in batches
def process_servers_batch(servers, batch_size=10):
    for i in range(0, len(servers), batch_size):
        batch = servers[i:i + batch_size]
        process_batch_parallel(batch)
        cleanup_batch_resources()
```

#### Incremental Auditing
```python
# Audit only changed servers
def incremental_audit(last_audit_time):
    changed_servers = get_servers_changed_since(last_audit_time)
    audit_servers(changed_servers)
```

#### Distributed Processing
```python
# Distribute work across multiple machines
def distributed_audit(servers, workers):
    chunks = split_servers(servers, workers)
    results = []
    for chunk in chunks:
        result = submit_to_worker(chunk)
        results.append(result)
    return aggregate_results(results)
```

---

## Performance Checklist

### Pre-Audit Checklist

- [ ] Verify hardware meets requirements
- [ ] Optimize Windows power settings
- [ ] Configure SQL Server connection pooling
- [ ] Test network connectivity to all targets
- [ ] Validate timeout settings for network conditions
- [ ] Check available disk space (> 2x expected audit size)
- [ ] Verify ODBC driver versions
- [ ] Test PowerShell remoting connectivity

### During Audit Checklist

- [ ] Monitor memory usage (< 80% of available RAM)
- [ ] Check CPU utilization (not consistently > 90%)
- [ ] Verify network bandwidth usage
- [ ] Monitor SQL Server performance impact
- [ ] Watch for connection timeouts
- [ ] Check log files for performance warnings

### Post-Audit Optimization

- [ ] Analyze performance metrics
- [ ] Optimize configuration based on results
- [ ] Archive old audit data
- [ ] Update baseline performance expectations
- [ ] Document performance tuning changes

---

*Performance guide reviewed: 2025-12-30 | AutoDBAudit v1.0.0*