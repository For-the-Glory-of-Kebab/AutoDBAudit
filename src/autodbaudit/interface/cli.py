"""
AutoDBAudit CLI entry point.

Main entry point for the application CLI.
"""

import sys
import argparse
import logging
from pathlib import Path

from autodbaudit.application.audit_service import AuditService
from autodbaudit.infrastructure.config_loader import ConfigLoader
from autodbaudit.infrastructure.logging_config import setup_logging
from autodbaudit.infrastructure.odbc_check import check_odbc_drivers


def main():
    """Main entry point for AutoDBAudit CLI."""
    parser = argparse.ArgumentParser(
        description="AutoDBAudit - SQL Server Security Audit Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Audit commands
    parser.add_argument("--audit", action="store_true",
                       help="Run SQL Server security audit")
    parser.add_argument("--config", type=str,
                       help="Path to audit configuration file")
    parser.add_argument("--targets", type=str,
                       help="Path to SQL targets configuration file")
    parser.add_argument("--append-to", type=str,
                       help="Append audit results to existing workbook (incremental)")
    
    # Remediation commands
    parser.add_argument("--generate-remediation", action="store_true",
                       help="Generate individual remediation scripts")
    parser.add_argument("--apply-remediation", action="store_true",
                       help="Apply remediation scripts (comment-aware)")
    parser.add_argument("--scripts", type=str,
                       help="Path to remediation scripts directory")
    
    # Hotfix deployment commands
    parser.add_argument("--deploy-hotfixes", action="store_true",
                       help="Deploy SQL Server hotfixes")
    parser.add_argument("--retry-failed", action="store_true",
                       help="Retry failed hotfix deployments")
    parser.add_argument("--resume", action="store_true",
                       help="Resume hotfix deployment after cancellation")
    
    # Utility commands
    parser.add_argument("--check-drivers", action="store_true",
                       help="Check available ODBC drivers")
    parser.add_argument("--setup-credentials", action="store_true",
                       help="Encrypt credentials interactively")
    parser.add_argument("--validate-config", action="store_true",
                       help="Validate configuration files")
    
    # Logging
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--log-file", type=str,
                       help="Write logs to file")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("AutoDBAudit starting...")
    
    try:
        if args.audit:
            logger.info("Running audit mode")
            # TODO: Implement audit workflow
            print("Audit mode - implementation pending")
        
        elif args.generate_remediation:
            logger.info("Generating remediation scripts")
            # TODO: Implement remediation generation
            print("Remediation generation - implementation pending")
        
        elif args.deploy_hotfixes:
            logger.info("Deploying hotfixes")
            # TODO: Implement hotfix deployment
            print("Hotfix deployment - implementation pending")
        
        elif args.check_drivers:
            check_odbc_drivers()
        
        else:
            parser.print_help()
            return 1
        
        logger.info("AutoDBAudit completed successfully")
        return 0
    
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
