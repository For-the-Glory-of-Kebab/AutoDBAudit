"""
SQL Query file loader.

Version Strategy:
- sql2008: For SQL Server 2008/2008 R2 (version_major <= 10)
- sql2019plus: For SQL Server 2012 and later (version_major >= 11)
  
We treat all modern versions as compatible with sql2019plus queries.
This can be refined later if version-specific queries are needed.

TODO: Add sql2022plus folder if 2022/2025 introduce incompatible syntax.
"""

import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# Version mapping constants
VERSION_MAJOR_2008 = 10   # SQL Server 2008 R2
VERSION_MAJOR_2012 = 11   # SQL Server 2012
VERSION_MAJOR_2014 = 12   # SQL Server 2014
VERSION_MAJOR_2016 = 13   # SQL Server 2016
VERSION_MAJOR_2017 = 14   # SQL Server 2017
VERSION_MAJOR_2019 = 15   # SQL Server 2019
VERSION_MAJOR_2022 = 16   # SQL Server 2022


def load_queries_for_version(base_queries_dir: Path, version_major: int) -> Dict[str, str]:
    """
    Load SQL queries appropriate for SQL Server version.
    
    Args:
        base_queries_dir: Base directory containing version specific subdirectories
        version_major: SQL Server major version (10=2008R2, 15=2019, 16=2022, etc.)
        
    Returns:
        Dictionary of query_name -> query_text
        
    Version Mapping:
        - version_major <= 10 (2008 R2): queries/sql2008/
        - version_major >= 11 (2012+):   queries/sql2019plus/
        
    Note: We currently treat 2012-2025+ as compatible with sql2019plus queries.
    If specific versions need different queries, add more folders later.
    """
    # Determine query directory based on version
    if version_major <= VERSION_MAJOR_2008:
        # SQL Server 2008 / 2008 R2 - legacy queries (no STRING_AGG, TRY_CAST, etc.)
        query_dir = base_queries_dir / "sql2008"
    else:
        # SQL Server 2012+ - modern queries
        # TODO: If 2022/2025 need specific queries, add sql2022plus folder
        query_dir = base_queries_dir / "sql2019plus"
    
    logger.info("Loading queries from: %s (SQL version_major=%d)", query_dir, version_major)
    
    queries = {}
    if query_dir.exists():
        for query_file in query_dir.glob("*.sql"):
            query_name = query_file.stem
            with open(query_file, 'r', encoding='utf-8') as f:
                queries[query_name] = f.read()
            logger.debug("Loaded query: %s", query_name)
    else:
        logger.warning("Query directory not found: %s", query_dir)
    
    logger.info("Loaded %d SQL queries", len(queries))
    return queries

