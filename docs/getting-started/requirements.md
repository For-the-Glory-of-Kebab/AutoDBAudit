# System Requirements

**Audience**: System administrators, IT security teams, database administrators
**Purpose**: Complete prerequisites for deploying and running AutoDBAudit
**Last Updated**: 2025-12-30

---

## Table of Contents

* [Operating System Requirements](#operating-system-requirements)
* [Python Environment](#python-environment)
* [SQL Server Requirements](#sql-server-requirements)
* [Network and Connectivity](#network-and-connectivity)
* [Permissions and Access Control](#permissions-and-access-control)
* [Hardware Requirements](#hardware-requirements)
* [Software Dependencies](#software-dependencies)
* [PowerShell Remoting Setup](#powershell-remoting-setup)
* [Excel and Office Integration](#excel-and-office-integration)
* [Security Considerations](#security-considerations)
* [Troubleshooting Prerequisites](#troubleshooting-prerequisites)

---

## Operating System Requirements

### Supported Platforms

**Windows Only** - AutoDBAudit is designed exclusively for Windows environments due to:

* SQL Server platform dependency
* PowerShell remoting requirements
* Windows-specific security APIs

### Windows Versions

| Windows Version | Support Level | Notes |
|----------------|---------------|-------|
| Windows Server 2022 | ✅ Fully Supported | Recommended for production |
| Windows Server 2019 | ✅ Fully Supported | Tested and validated |
| Windows Server 2016 | ✅ Supported | May require updates |
| Windows 11 | ✅ Supported | Development/testing only |
| Windows 10 | ✅ Supported | Development/testing only |
| Windows Server 2012 R2 | ⚠️ Limited | EOL, may have compatibility issues |

### Windows Features Required

**PowerShell Remoting (WinRM)**:
```powershell
# Enable WinRM (run as Administrator)
Enable-PSRemoting -Force

# Configure TrustedHosts for remote connections
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

**Windows Firewall**:
- Must allow WinRM traffic (ports 5985/5986)
- SQL Server ports (default 1433, or configured ports)

---

## Python Environment

### Python Version Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Python Interpreter | ≥ 3.11 | Required for type hints and modern features |
| pip | ≥ 23.0 | For dependency management |
| setuptools | ≥ 61.0 | For package building |

### Virtual Environment

**Required** - Isolated Python environment prevents conflicts:

```bash
# Create virtual environment
python -m venv autodbaudit_env

# Activate environment
.\autodbaudit_env\Scripts\activate  # Windows
# source autodbaudit_env/bin/activate  # Linux/Mac (not supported)

# Install dependencies
pip install -r requirements.txt
```

### Python Dependencies

#### Core Runtime Dependencies

| Package | Version | Purpose | Installation |
|---------|---------|---------|-------------|
| `pyodbc` | ≥ 5.0.0 | SQL Server connectivity | `pip install pyodbc>=5.0.0` |
| `openpyxl` | ≥ 3.1.0 | Excel file manipulation | `pip install openpyxl>=3.1.0` |
| `rich` | ≥ 13.0.0 | Enhanced CLI output | `pip install rich>=13.0.0` |
| `pillow` | ≥ 10.0.0 | Image processing for Excel | `pip install pillow>=10.0.0` |
| `pywin32` | ≥ 306 | Windows API access | `pip install pywin32>=306` |
| `jinja2` | ≥ 3.0 | Template rendering | `pip install jinja2>=3.0` |
| `pywinrm` | ≥ 0.4.0 | PowerShell remoting | `pip install pywinrm>=0.4.0` |

#### Development Dependencies (Optional)

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥ 7.0 | Unit testing |
| `pytest-cov` | ≥ 4.0 | Test coverage |
| `hypothesis` | ≥ 6.0 | Property-based testing |
| `mypy` | ≥ 1.0 | Type checking |
| `ruff` | ≥ 0.1.0 | Code linting |

---

## SQL Server Requirements

### Supported SQL Server Versions

| SQL Server Version | Support Level | Notes |
|-------------------|---------------|-------|
| SQL Server 2022 | ✅ Fully Supported | Latest features supported |
| SQL Server 2019 | ✅ Fully Supported | Standard and Enterprise |
| SQL Server 2017 | ✅ Supported | May have limited features |
| SQL Server 2016 | ✅ Supported | SP2+ recommended |
| SQL Server 2014 | ⚠️ Limited | EOL, basic functionality only |
| SQL Server 2012 | ⚠️ Limited | EOL, compatibility mode |
| SQL Server 2008 R2 | ⚠️ Limited | EOL, legacy support only |

### SQL Server Editions

* **Express**: ✅ Supported (development/testing)
* **Standard**: ✅ Fully Supported
* **Enterprise**: ✅ Fully Supported
* **Developer**: ✅ Supported (development)

### ODBC Driver Requirements

**Microsoft ODBC Driver for SQL Server**:

| Driver Version | SQL Server Support | Download |
|----------------|-------------------|----------|
| ODBC 18.x | SQL Server 2012+ | [Microsoft Download](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) |
| ODBC 17.x | SQL Server 2008+ | Legacy support |

**Installation Verification**:
```powershell
# Check ODBC drivers
Get-OdbcDriver -Name "*SQL Server*"
```

### SQL Server Configuration

#### Required Permissions

**Database Access**:
- `VIEW SERVER STATE` permission
- `SELECT` on system DMVs and catalog views
- Access to `master`, `msdb`, and user databases

**Server-Level Permissions**:
- `CONNECT SQL` permission
- `VIEW ANY DEFINITION` permission
- Access to server-level configuration

#### Authentication Methods

**SQL Server Authentication**:
- Login with appropriate permissions
- Password stored securely in credentials file

**Windows Authentication**:
- Domain account with required permissions
- Kerberos authentication preferred

---

## Network and Connectivity

### Network Protocols

**TCP/IP**:
- SQL Server default port: 1433
- Named instances: Dynamic ports or configured ports
- WinRM: 5985 (HTTP), 5986 (HTTPS)

**Named Pipes** (Alternative):
- Supported but TCP/IP preferred
- Local connections only

### Firewall Configuration

**SQL Server Ports**:
```powershell
# Allow SQL Server traffic
New-NetFirewallRule -DisplayName "SQL Server" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow
```

**WinRM Ports**:
```powershell
# Allow WinRM HTTP
New-NetFirewallRule -DisplayName "WinRM HTTP" -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow

# Allow WinRM HTTPS (recommended)
New-NetFirewallRule -DisplayName "WinRM HTTPS" -Direction Inbound -Protocol TCP -LocalPort 5986 -Action Allow
```

### DNS Resolution

**Requirements**:
- Forward and reverse DNS resolution
- Consistent hostname resolution
- IPv4 and IPv6 support (IPv4 preferred)

---

## Permissions and Access Control

### Local System Permissions

**Running AutoDBAudit**:
- Local administrator rights (for WinRM configuration)
- Write access to output directories
- Read access to configuration files

### SQL Server Permissions Matrix

| Operation | Required Permission | Scope |
|-----------|-------------------|-------|
| Database enumeration | `VIEW ANY DATABASE` | Server |
| Login enumeration | `VIEW ANY DEFINITION` | Server |
| Server configuration | `VIEW SERVER STATE` | Server |
| Database properties | `SELECT` on `sys.databases` | Server |
| User permissions | `SELECT` on `sys.server_permissions` | Server |

### PowerShell Remoting Permissions

**Target Server Access**:
- Domain administrator credentials (recommended)
- Local administrator on target servers
- WinRM remote management permissions

**Credential Requirements**:
- Domain account for Kerberos authentication
- Local account for workgroup scenarios
- Service account with appropriate permissions

---

## Hardware Requirements

### Minimum Hardware

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| CPU | 2 cores | 4+ cores | Multi-threading for parallel operations |
| RAM | 4 GB | 8 GB+ | Depends on database size and concurrent operations |
| Storage | 1 GB | 10 GB+ | For audit data, Excel files, and logs |
| Network | 100 Mbps | 1 Gbps | For remote SQL Server connections |

### Storage Considerations

**Working Directory**:
- 500 MB for application files
- Variable space for Excel outputs (depends on findings)
- SQLite database growth (typically < 100 MB per audit)

**Temporary Files**:
- PowerShell script generation
- Excel processing temporary files
- Log file accumulation

### Performance Scaling

**Large Environments**:
- 16+ GB RAM for 100+ servers
- SSD storage for faster Excel processing
- Multi-core CPU for parallel audit execution

---

## Software Dependencies

### Required Windows Features

**PowerShell 5.1+**:
```powershell
# Check PowerShell version
$PSVersionTable.PSVersion
```

**Windows Remote Management**:
```powershell
# Verify WinRM installation
Get-Service WinRM
Test-WSMan -ComputerName localhost
```

### Optional but Recommended

**Microsoft Excel**:
- For manual review of audit reports
- Not required for automated processing

**SQL Server Management Studio (SSMS)**:
- For manual verification of findings
- Database administration tasks

---

## PowerShell Remoting Setup

### WinRM Configuration

**Automatic Setup** (via `prepare` command):
```bash
python main.py prepare --targets sql_targets.json
```

**Manual Setup** (if automatic fails):
```powershell
# Enable PS Remoting
Enable-PSRemoting -Force

# Configure authentication
Set-Item WSMan:\localhost\Service\Auth\Kerberos -Value $true
Set-Item WSMan:\localhost\Service\Auth\Negotiate -Value $true
Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true

# Configure TrustedHosts
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

### Registry Settings

**Required for Local Account Authentication**:
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\LocalAccountTokenFilterPolicy = 1
```

**Required for Loopback Authentication**:
```
HKLM\SYSTEM\CurrentControlSet\Control\Lsa\DisableLoopbackCheck = 1
```

### SSL/TLS Configuration (Recommended)

**Certificate Requirements**:
- Valid SSL certificate for HTTPS WinRM
- Certificate thumbprint configuration
- HTTPS listener on port 5986

---

## Excel and Office Integration

### Excel Version Support

| Excel Version | Support Level | Notes |
|----------------|---------------|-------|
| Excel 2021 | ✅ Fully Supported | Desktop and Office 365 |
| Excel 2019 | ✅ Fully Supported | Desktop |
| Excel 2016 | ✅ Supported | SP2+ recommended |
| Excel 2013 | ⚠️ Limited | Basic functionality |
| Excel Online | ✅ Supported | Web version |

### Excel Features Used

**Required Features**:
- XLSX file format support
- Conditional formatting
- Data validation
- Charts and graphs
- Image insertion (for icons)

**Optional Features**:
- VBA macros (not used)
- External data connections (not used)

### Alternative Office Suites

**LibreOffice/OpenOffice**:
- ⚠️ Limited support
- Basic Excel file reading/writing
- Advanced formatting may not work

---

## Security Considerations

### Credential Management

**Secure Storage**:
- Encrypted credential files
- Windows Credential Manager integration
- No plaintext passwords in logs

**Access Control**:
- Restrict access to credential files
- Use least-privilege accounts
- Audit credential access

### Network Security

**Encryption**:
- SSL/TLS for WinRM (recommended)
- Encrypted SQL Server connections
- VPN for remote access

**Firewall Rules**:
- Minimal required ports open
- IP address restrictions
- Time-based access rules

### Audit Logging

**AutoDBAudit Logging**:
- Comprehensive audit trails
- Error and access logging
- Configurable log levels

**System Logging**:
- Windows Event Logs
- SQL Server audit logs
- PowerShell transcription

---

## Troubleshooting Prerequisites

### Common Issues

**ODBC Connection Errors**:
```bash
# Test ODBC connection
python -c "import pyodbc; print(pyodbc.drivers())"
```

**WinRM Connection Issues**:
```powershell
# Test WinRM connectivity
Test-WSMan -ComputerName target-server
```

**Permission Errors**:
- Verify SQL Server permissions
- Check Windows user rights
- Validate credential files

### Diagnostic Tools

**Built-in Diagnostics**:
```bash
# Run diagnostic checks
python main.py util --diagnostics
```

**External Tools**:
- SQL Server Configuration Manager
- Windows Event Viewer
- PowerShell remoting tests

### Support Resources

**Documentation**:
- [AutoDBAudit User Guide](user-guide/README.md)
- [CLI Reference](cli/reference.md)
- [Troubleshooting Guide](deployment/troubleshooting.md)

**Community Support**:
- GitHub Issues
- Documentation feedback
- Community forums

---

*Prerequisites verified: 2025-12-30 | AutoDBAudit v1.0.0*