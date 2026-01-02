# Prepare Subcommand: PowerShell Remoting Setup

**Purpose**: The `prepare` subcommand is a prerequisite setup tool that configures PowerShell remoting (WinRM) on target machines to enable reliable OS-level data collection during audits and sync operations. It ensures that the audit process can use PowerShell remoting for collecting data that T-SQL cannot access (e.g., Windows services, registry settings, client protocols).

**Source Code**: `src/autodbaudit/interface/cli.py` (prepare command implementation)

**Status**: Currently **IN DEVELOPMENT** - Implementing comprehensive PS remoting setup with server consolidation, 5-layer strategy, and manual override fallbacks. See `docs/cli/reference.md` for updated command specifications.

## Vision and Requirements

### Core Purpose

The prepare phase establishes secure, authenticated PowerShell remoting connections to all target SQL Server machines. This is essential because:

- **Hybrid Data Collection**: Audit/sync uses T-SQL for database-internal data + PowerShell for OS-level data
- **Fallback Strategy**: Prioritizes PS remoting when available; falls back to T-SQL/cached data if PS fails
- **Security**: Uses explicit Windows domain credentials (promised to be domain admin level)

### Target Configuration Scope

For each server in `sql_targets.json`:

- **Server Entry Format**: IP address + port, or hostname + instance name
- **Instance Name Issue**: Current acquisition logic incorrectly marks most as "Default" instance when they are named instances
- **Credentials**:
  - SQL creds in `credentials.json` (username/password for SQL auth)
  - Windows creds in separate JSON key (domain admin user for PS remoting)

### Comprehensive PS Remoting Access Strategy

**Philosophy**: Exhaustive, flexible, and persistent. Try every possible combination of authentication methods, connection protocols, ports, and configuration changes until PS remoting works. Don't restrict to "Microsoft best practices" - use whatever works.

**Key Principles**:

- **No Permission Limits**: Domain admin credentials provide full access - use them aggressively
- **Try Everything**: Every auth method, every port, every protocol, every configuration tweak
- **Learn and Reuse**: Remember what worked for each server and reuse automatically
- **Shared Logic**: Same connection logic used in prepare, sync, and remediate phases
- **State Persistence**: Store successful connection parameters per server

### Exhaustive Failure Mode Analysis

**Authentication Hurdles**:

- Kerberos (domain) vs NTLM (workgroup/IP) vs Negotiate vs Basic vs CredSSP
- Missing pykerberos library causing Kerberos failures
- Double-hop issues requiring CredSSP
- Certificate-based authentication (SSL/TLS)
- Local account restrictions on workgroup machines

**Connection Hurdles**:

- HTTP (5985) vs HTTPS (5986) vs SSH (22)
- Firewall blocking WinRM ports
- TrustedHosts not configured for IP connections
- Network profiles (Public/Private/Domain) blocking access
- Proxy server interference
- IPv6 vs IPv4 issues

**Service/Configuration Hurdles**:

- WinRM service not running or not set to Automatic
- WinRM listeners not configured
- SPN (Service Principal Name) issues
- Group Policy restrictions
- Local security policies blocking remote access

**Credential Hurdles**:

- Wrong credential format or encoding
- Domain vs local account confusion
- Password expiration or lockout
- Multi-factor authentication requirements
- Credential delegation issues

**Platform Hurdles**:

- Windows version differences (Server vs Client vs Core)
- PowerShell version compatibility
- .NET Framework issues
- Localhost/loopback restrictions
- **LocalAccountTokenFilterPolicy**: Missing registry setting preventing local account remote authentication
- **DisableLoopbackCheck**: Missing registry setting causing localhost authentication failures

### Multi-Layered Connection Strategy

#### Layer 1: Direct Connection Attempts (No Changes)

Try all possible connection methods without modifying target:

1. **Standard PS Remoting**:
   - `Enter-PSSession -ComputerName $target`
   - Try with/without explicit credentials
   - Try different authentication methods: Default, Kerberos, NTLM, Negotiate, Basic, CredSSP

2. **Alternative Ports/Protocols**:
   - HTTP (5985), HTTPS (5986), SSH (22)
   - Custom ports if configured
   - Different transport protocols

3. **Connection Options**:
   - Different session options (-SkipCACheck, -SkipCNCheck, etc.)
   - Different timeout values
   - Different buffer sizes

#### Layer 2: Client-Side Configuration

Modify local (audit machine) settings to enable connections:

1. **TrustedHosts Management**:
   - Add target IPs/hostnames to TrustedHosts
   - Try wildcard (*) if specific entries fail
   - Handle IPv6 addresses

2. **WinRM Client Configuration**:
   - Adjust client timeout settings
   - Configure proxy settings if needed
   - Set maximum connections/envelope sizes

3. **Credential Preparation**:
   - Convert credentials to PSCredential objects
   - Handle different credential formats
   - Test credential validity

#### Layer 3: Target Machine Configuration (Remote Setup)

Use domain admin credentials to modify target machines:

1. **WinRM Service Management**:
   - Start WinRM service
   - Set startup type to Automatic
   - Enable WinRM through firewall

2. **Firewall Configuration**:
   - Add WinRM HTTP/HTTPS rules
   - Handle different network profiles (Public/Private/Domain)
   - Configure custom ports if needed

3. **WinRM Listener Setup**:
   - Create HTTP and HTTPS listeners
   - Configure authentication methods
   - Set up SSL certificates for HTTPS

4. **Security Policy Adjustments**:
   - Modify local security policies for remote access
   - Handle UAC restrictions
   - Configure service permissions
   - **LocalAccountTokenFilterPolicy**: Allow local accounts to authenticate remotely (critical for workgroup scenarios)
   - **DisableLoopbackCheck**: Disable authentication loopback check for localhost connections

#### Layer 4: Advanced Configuration and Fallbacks

If standard WinRM fails, try alternative approaches:

1. **SSH-Based PowerShell**:
   - Use OpenSSH for PowerShell remoting
   - Configure SSH keys or passwords
   - Handle SSH host key verification

2. **WMI/RPC Fallbacks**:
   - Direct WMI connections
   - RPC-based remote execution
   - DCOM configuration

3. **Alternative Tools**:
   - psexec for command execution
   - schtasks for scheduled task creation
   - Custom PowerShell scripts via other channels

#### Layer 5: Manual Override and Logging

If all automated methods fail:

1. **Detailed Error Logging**:
   - Log every attempt with specific error codes
   - Capture network traces if possible
   - Record system state before/after changes

2. **Manual Intervention Points**:
   - Generate detailed setup instructions for user
   - Provide PowerShell scripts for manual execution
   - Allow user to specify custom connection parameters

3. **Graceful Degradation**:
   - Fall back to T-SQL only mode
   - Use cached data from previous successful connections
   - Mark server as requiring manual setup

### State Persistence and Learning

**Per-Server Connection Profiles**:

- Store successful connection parameters in database
- Include: auth method, port, protocol, credential format, custom options
- Update profiles when new methods work or old ones fail

**Automatic Reuse**:

- Prepare phase discovers working methods
- Sync/remediate phases use stored successful parameters
- Fall back to discovery if stored methods fail

**Connection Health Monitoring**:

- Periodic validation of stored connection methods
- Automatic rediscovery if connections break
- Alert when previously working servers become inaccessible

### Shared Modular Architecture

**Core Connection Module** (`src/autodbaudit/infrastructure/psremoting/`):

- `connection_manager.py`: Main connection logic
- `auth_methods.py`: All authentication method implementations
- `config_manager.py`: WinRM configuration management
- `credential_handler.py`: Credential preparation and validation
- `fallback_strategies.py`: Alternative connection methods

**Integration Points**:

- **Prepare Phase**: Uses full discovery and configuration
- **Sync Phase**: Uses stored profiles with fallback to discovery
- **Remediate Phase**: Uses stored profiles, revalidates before execution

**API Design**:

```python
class PSRemotingManager:
    def connect(self, server: str, credentials: dict) -> PSSession:
        # Try all methods until one works
        
    def ensure_access(self, server: str, credentials: dict, allow_config: bool = True) -> ConnectionProfile:
        # Full setup if allowed, connection test if not
        
    def get_stored_profile(self, server: str) -> ConnectionProfile:
        # Retrieve successful parameters from database
```

### Credential Handling Fixes

**Current Issue**: Prepare works but sync/remediate doesn't pass credentials

**Root Cause**: Different code paths don't share credential handling logic

**Solution**:

1. **Unified Credential Pipeline**: Same credential preparation in all phases
2. **PSCredential Object Creation**: Convert JSON credentials to PowerShell-compatible objects
3. **Authentication Method Selection**: Choose auth method based on what worked in prepare
4. **Error Handling**: Detailed logging when credential passing fails

**Implementation**:

- Store credential format preferences per server
- Validate credentials before use
- Handle credential expiration/rotation
- Support different credential storage formats (encrypted JSON, Windows Credential Manager, etc.)

## Current Implementation Issues

### Broken Features

1. **Random Failures**: Setup succeeds intermittently, fails unpredictably
2. **Service Enablement**: Does not reliably start/enable WinRM service on targets
3. **Firewall Rules**: Fails to add necessary WinRM firewall exceptions
4. **Authentication Reliance**: Only works with NTLM + HTTP, errors on missing pykerberos for Kerberos
5. **TrustedHosts Missing**: Never adds target IPs to TrustedHosts, causing connection failures
6. **Localhost Setup**: Does not configure local machine for testing
7. **Instance Name Bug**: Incorrectly identifies named instances as "Default"
8. **Credential Handling**: In sync/remediation, fails to pass explicit credentials for PS remoting

### Root Causes

- Incomplete WinRM configuration (missing firewall rules, listeners)
- No TrustedHosts management
- Authentication method hardcoded to NTLM without fallbacks
- No state tracking for revert functionality
- Missing localhost handling
- Instance enumeration logic flawed

### Impact on Audit/Sync

- PS remoting fails → Falls back to T-SQL only → Incomplete data collection
- Manual fixes required (RDP, manual WinRM setup) → Time-consuming, error-prone
- Even after manual fix, sync/remediation doesn't pass credentials → Still fails

### Implementation Phases

#### Phase 1: Core PS Remoting Module (Priority: High)

Create the shared PS remoting infrastructure:

1. **Connection Manager** (`src/autodbaudit/infrastructure/psremoting/connection_manager.py`):
   - `try_all_methods()`: Exhaustive connection attempts
   - `connect_with_profile()`: Use stored successful parameters
   - `discover_working_method()`: Find what works for new servers

2. **Authentication Handler** (`src/autodbaudit/infrastructure/psremoting/auth_methods.py`):
   - Implement all auth methods: Kerberos, NTLM, Negotiate, Basic, CredSSP
   - Handle credential conversion and validation
   - Detect and handle missing libraries (pykerberos, etc.)

3. **Configuration Manager** (`src/autodbaudit/infrastructure/psremoting/config_manager.py`):
   - TrustedHosts management (add/remove/revert)
   - WinRM service control (start/stop/enable)
   - Firewall rule management
   - Listener creation and configuration

4. **Credential Handler** (`src/autodbaudit/infrastructure/psremoting/credential_handler.py`):
   - Convert JSON credentials to PSCredential objects
   - Handle different credential formats
   - Validate credential usability

5. **Fallback Strategies** (`src/autodbaudit/infrastructure/psremoting/fallback_strategies.py`):
   - SSH-based PowerShell
   - WMI/RPC connections
   - psexec/schtasks alternatives

#### Phase 2: Database Schema for Connection Profiles

Add tables to store successful connection parameters:

```sql
CREATE TABLE psremoting_profiles (
    server_name VARCHAR(255) PRIMARY KEY,
    auth_method VARCHAR(50),
    port INT,
    protocol VARCHAR(10), -- HTTP, HTTPS, SSH
    credential_format VARCHAR(50),
    custom_options JSON,
    last_successful DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE psremoting_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    server_name VARCHAR(255),
    auth_method VARCHAR(50),
    port INT,
    protocol VARCHAR(10),
    error_message TEXT,
    attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_server_attempted (server_name, attempted_at)
);
```

#### Phase 3: Prepare Command Integration

Update the prepare subcommand to use the new module:

1. **Full Discovery Mode**: Try all methods, configure as needed
2. **Profile Storage**: Save successful parameters to database
3. **Revert Support**: Track and undo all changes
4. **Progress Reporting**: Detailed logging of attempts and successes

#### Phase 4: Sync/Remediate Integration

Modify sync and remediate phases to reuse prepare results:

1. **Profile Lookup**: Check database for stored successful parameters
2. **Connection Reuse**: Use stored profiles first
3. **Fallback Logic**: Rediscover if stored methods fail
4. **Credential Passing Fix**: Use unified credential handling

#### Phase 5: Testing and Validation

Comprehensive testing strategy:

1. **Unit Tests**: Test each auth method and configuration change
2. **Integration Tests**: Full prepare → sync → remediate workflow
3. **Real Environment Tests**: Test with various server configurations
4. **Error Simulation**: Test failure modes and recovery

### Security Considerations

**Principle of Least Privilege**:

- Use domain admin only when necessary for configuration
- Store credentials encrypted and access-controlled
- Audit all configuration changes

**Revertibility**:

- Track all changes made to target systems
- Provide perfect revert capability
- Log all modifications for compliance

**Network Security**:

- Prefer HTTPS over HTTP when possible
- Validate certificates properly
- Use secure authentication methods (Kerberos over NTLM)

**Credential Protection**:

- Never log credentials in plain text
- Use secure credential storage
- Handle credential rotation and expiration

### Future Enhancements

- **Certificate Management**: Auto-provision SSL certificates
- **Group Policy Integration**: For enterprise deployments
- **Monitoring**: Real-time WinRM health checks
