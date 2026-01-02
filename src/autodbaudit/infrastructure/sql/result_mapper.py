"""
Ultimate T-SQL Result Mapper - Type-Safe SQL to Object Mapping

This module provides:
1. Automatic mapping from SQL column names to Python field names
2. Type coercion and validation with Pydantic
3. Null value handling
4. Relationship resolution for joined queries
5. Integration with existing collectors

Usage:
    # Instead of manual dict mapping:
    # OLD: users = [User(name=row['name'], id=row['user_id']) for row in results]

    # NEW: users = sql_mapper.map_to_models(results, UserModel,
    #                                      field_mapping={'user_id': 'id'})

    # Even better - automatic mapping:
    # users = sql_mapper.map_to_models(results, UserModel)  # Uses naming conventions
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, get_type_hints
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# ============================================================================
# Type-Safe SQL Result Models
# ============================================================================

class LoginModel(BaseModel):
    """Type-safe model for SQL Server logins."""
    name: str = Field(..., alias="LoginName")
    principal_id: Optional[int] = Field(None, alias="PrincipalId")
    login_type: str = Field(..., alias="LoginType")
    is_disabled: bool = Field(..., alias="IsDisabled")
    create_date: Optional[datetime] = Field(None, alias="CreateDate")
    default_database: Optional[str] = Field(None, alias="DefaultDatabase")
    password_policy: Optional[bool] = Field(None, alias="PasswordPolicyEnforced")
    password_expiration: Optional[bool] = Field(None, alias="PasswordExpirationEnabled")

    class Config:
        allow_population_by_field_name = True

class DatabaseModel(BaseModel):
    """Type-safe model for databases."""
    database_id: int = Field(..., alias="DatabaseId")
    name: str = Field(..., alias="DatabaseName")
    collation: Optional[str] = Field(None, alias="Collation")
    recovery_model: str = Field(..., alias="RecoveryModel")
    state: str = Field(..., alias="State")
    owner: Optional[str] = Field(None, alias="Owner")
    size_mb: Optional[float] = Field(None, alias="SizeMB")
    data_size_mb: Optional[float] = Field(None, alias="DataSizeMB")
    log_size_mb: Optional[float] = Field(None, alias="LogSizeMB")

class ServerPropertyModel(BaseModel):
    """Type-safe model for server properties."""
    server_name: str = Field(..., alias="ServerName")
    instance_name: Optional[str] = Field(None, alias="InstanceName")
    machine_name: str = Field(..., alias="MachineName")
    version: str = Field(..., alias="Version")
    version_major: int = Field(..., alias="VersionMajor")
    edition: str = Field(..., alias="Edition")
    product_level: str = Field(..., alias="ProductLevel")
    cpu_count: int = Field(..., alias="CPUCount")
    memory_gb: float = Field(..., alias="MemoryGB")

class ConfigurationModel(BaseModel):
    """Type-safe model for sp_configure results."""
    name: str = Field(..., alias="SettingName")
    configured_value: int = Field(..., alias="ConfiguredValue")
    running_value: int = Field(..., alias="RunningValue")
    minimum: int = Field(..., alias="MinValue")
    maximum: int = Field(..., alias="MaxValue")
    is_dynamic: bool = Field(..., alias="IsDynamic")
    is_advanced: bool = Field(..., alias="IsAdvanced")
    description: str = Field(..., alias="Description")

# ============================================================================
# Ultimate SQL Result Mapper
# ============================================================================

class SqlResultMapper:
    """
    Ultimate mapper from SQL results to type-safe Python objects.

    Features:
    - Automatic column name to field name mapping (snake_case, camelCase)
    - Type coercion and validation
    - Null handling with sensible defaults
    - Relationship resolution for joined queries
    - Integration with existing codebase
    """

    @staticmethod
    def _normalize_column_name(sql_column: str) -> str:
        """Convert SQL column names to Python field names."""
        # Handle common SQL naming patterns
        name = sql_column

        # Convert PascalCase to snake_case
        # Insert underscore before uppercase letters (but not at start)
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

        # Handle special cases
        replacements = {
            'cpu_count': 'cpu_count',
            'memory_gb': 'memory_gb',
            'size_mb': 'size_mb',
            'data_size_mb': 'data_size_mb',
            'log_size_mb': 'log_size_mb',
            'database_id': 'database_id',
            'server_name': 'server_name',
            'instance_name': 'instance_name',
            'machine_name': 'machine_name',
            'version_major': 'version_major',
            'product_level': 'product_level',
            'login_name': 'name',  # Special mapping for logins
            'database_name': 'name',  # Special mapping for databases
            'setting_name': 'name',  # Special mapping for config
        }

        return replacements.get(name, name)

    @staticmethod
    def _coerce_value(value: Any, target_type: Type) -> Any:
        """Coerce SQL value to target Python type."""
        if value is None:
            # Return None for Optional types, default for others
            if hasattr(target_type, '__origin__') and target_type.__origin__ is Union:
                # Optional[T] is Union[T, None]
                return None
            # For non-optional types, provide sensible defaults
            if target_type == int:
                return 0
            elif target_type == float:
                return 0.0
            elif target_type == str:
                return ""
            elif target_type == bool:
                return False
            elif target_type == datetime:
                return None
            else:
                return None

        # Type coercion
        try:
            if target_type == bool:
                # SQL Server BIT/INT -> bool
                return bool(int(value))
            elif target_type == int:
                return int(float(value)) if isinstance(value, str) else int(value)
            elif target_type == float:
                return float(value)
            elif target_type == str:
                return str(value)
            elif target_type == datetime:
                if isinstance(value, str):
                    # Try ISO format first, then common SQL formats
                    try:
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        # Fallback to basic parsing
                        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                return value
            else:
                return value
        except (ValueError, TypeError):
            logger.warning("Failed to coerce %s to %s, using default", value, target_type)
            return SqlResultMapper._coerce_value(None, target_type)

    @classmethod
    def map_to_models(
        cls,
        sql_results: List[Dict[str, Any]],
        model_class: Type[T],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[T]:
        """
        Map SQL result rows to Pydantic models with automatic type safety.

        Args:
            sql_results: Raw SQL query results (List[Dict])
            model_class: Target Pydantic model class
            field_mapping: Optional explicit column -> field mapping

        Returns:
            List of validated model instances
        """
        models = []

        # Get model field types
        field_types = get_type_hints(model_class)

        for row in sql_results:
            model_data = {}

            for sql_column, value in row.items():
                # Determine target field name
                if field_mapping and sql_column in field_mapping:
                    field_name = field_mapping[sql_column]
                else:
                    field_name = cls._normalize_column_name(sql_column)

                # Skip if field doesn't exist on model
                if field_name not in field_types:
                    continue

                # Coerce value to correct type
                target_type = field_types[field_name]
                coerced_value = cls._coerce_value(value, target_type)

                model_data[field_name] = coerced_value

            try:
                # Create model instance with validation
                model = model_class(**model_data)
                models.append(model)
            except Exception as e:
                logger.warning("Failed to create %s from row %s: %s", model_class.__name__, row, e)
                continue

        return models

    @classmethod
    def map_single_to_model(
        cls,
        sql_result: Dict[str, Any],
        model_class: Type[T],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> Optional[T]:
        """Map single SQL result row to model."""
        models = cls.map_to_models([sql_result], model_class, field_mapping)
        return models[0] if models else None

# ============================================================================
# Integration with Existing Collectors
# ============================================================================

class CollectorResultMapper:
    """
    Integration layer for existing collectors.

    Provides drop-in replacements for manual dict-to-object mapping.
    """

    def __init__(self):
        self.mapper = SqlResultMapper()

    def map_logins(self, sql_results: List[Dict[str, Any]]) -> List[LoginModel]:
        """Map server login query results."""
        return self.mapper.map_to_models(sql_results, LoginModel)

    def map_databases(self, sql_results: List[Dict[str, Any]]) -> List[DatabaseModel]:
        """Map database query results."""
        return self.mapper.map_to_models(sql_results, DatabaseModel)

    def map_server_properties(self, sql_results: List[Dict[str, Any]]) -> List[ServerPropertyModel]:
        """Map server property query results."""
        return self.mapper.map_to_models(sql_results, ServerPropertyModel)

    def map_configurations(self, sql_results: List[Dict[str, Any]]) -> List[ConfigurationModel]:
        """Map sp_configure query results."""
        return self.mapper.map_to_models(sql_results, ConfigurationModel)

# ============================================================================
# Usage Examples and Migration Guide
# ============================================================================

def migration_example():
    """
    How to migrate existing collectors to use type-safe mapping.

    BEFORE (manual mapping, error-prone):
    ```python
    def collect_server_logins(self) -> List[Dict[str, Any]]:
        results = self.conn.execute_query(self.prov.get_server_logins())

        # Manual dict-to-object mapping - repetitive and error-prone
        logins = []
        for row in results:
            login = {
                'name': row.get('LoginName', ''),
                'type': row.get('LoginType', 'Unknown'),
                'disabled': bool(row.get('IsDisabled', False)),
                'create_date': row.get('CreateDate'),
            }
            logins.append(login)
        return logins
    ```

    AFTER (type-safe, automatic):
    ```python
    def collect_server_logins(self) -> List[LoginModel]:
        results = self.conn.execute_query(self.prov.get_server_logins())

        # Automatic mapping with validation
        mapper = CollectorResultMapper()
        return mapper.map_logins(results)
    ```
    """

    # Example data from SQL Server
    sample_login_results = [
        {
            "LoginName": "sa",
            "PrincipalId": 1,
            "LoginType": "SQL",
            "IsDisabled": False,
            "CreateDate": "2020-01-01T00:00:00",
            "DefaultDatabase": "master",
            "PasswordPolicyEnforced": True,
            "PasswordExpirationEnabled": True
        },
        {
            "LoginName": "ADMIN\\Administrator",
            "PrincipalId": 2,
            "LoginType": "Windows",
            "IsDisabled": False,
            "CreateDate": "2020-01-01T00:00:00",
            "DefaultDatabase": None,
            "PasswordPolicyEnforced": None,
            "PasswordExpirationEnabled": None
        }
    ]

    # Type-safe mapping
    mapper = CollectorResultMapper()
    logins = mapper.map_logins(sample_login_results)

    print(f"Mapped {len(logins)} login objects:")
    for login in logins:
        print(f"  - {login.name} ({login.login_type}) - Disabled: {login.is_disabled}")

    # Benefits:
    # 1. Type safety - IDE autocomplete, type checking
    # 2. Validation - Pydantic ensures data integrity
    # 3. No manual mapping code
    # 4. Automatic null handling
    # 5. Consistent field naming

if __name__ == "__main__":
    migration_example()
