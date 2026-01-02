"""
Parallel processor - Ultra-granular parallel processing logic.

This module provides specialized functionality for processing targets
in parallel using thread pools and dynamic worker management.
"""

import logging
import concurrent.futures
from typing import List

from autodbaudit.application.container import Container
from autodbaudit.domain.config.audit_settings import AuditSettings
from autodbaudit.domain.config.models.prepare_result import PrepareResult

logger = logging.getLogger(__name__)


class ParallelProcessor:
    """Ultra-granular parallel processing logic."""

    def __init__(self, container: Container, audit_settings: AuditSettings):
        self.container = container
        self.audit_settings = audit_settings

    def process_targets_parallel(self, targets: List) -> List:
        """Process targets in parallel."""
        max_workers = min(self.audit_settings.max_parallel_targets, len(targets))
        logger.info("Preparing %d targets with %d parallel workers", len(targets), max_workers)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_target = {
                executor.submit(self.container.prepare_service.prepare_target, target): target
                for target in targets
            }

            for future in concurrent.futures.as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug("Completed preparation for target: %s", target.name)
                except Exception as e:
                    logger.error("Preparation failed for target %s: %s", target.name, e)
                    failure_result = PrepareResult.failure_result(
                        target, f"Parallel preparation failed: {e}", [f"Error: {e}"]
                    )
                    results.append(failure_result)

        return results
