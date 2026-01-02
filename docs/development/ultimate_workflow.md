# Ultimate Development Workflow - Phase 1-4 Implementation

## Overview
This document outlines the complete 4-phase development approach for transforming your SQL audit tool into a modern, maintainable, and robust system.

## Phase 1: Architecture Foundation (DDD + Dependency Injection + Result Types)

### Goals
- Establish clean architecture with proper separation of concerns
- Implement dependency injection for testability
- Add Result types (Railway-oriented programming) for error handling
- Create domain models with business logic

### Implementation Steps

#### 1.1 Domain Layer (Business Logic)
```python
# src/autodbaudit/domain/models.py (extend existing)
@dataclass
class AuditRun:
    id: Optional[int] = None
    status: AuditStatus = AuditStatus.PENDING
    # ... existing fields

    def can_transition_to(self, new_status: AuditStatus) -> bool:
        """Business rule: valid status transitions"""
        transitions = {
            AuditStatus.PENDING: [AuditStatus.RUNNING],
            AuditStatus.RUNNING: [AuditStatus.COMPLETED, AuditStatus.FAILED],
            AuditStatus.COMPLETED: [],  # Terminal state
            AuditStatus.FAILED: [AuditStatus.RUNNING],  # Can retry
        }
        return new_status in transitions.get(self.status, [])

# src/autodbaudit/domain/services/audit_service.py
class AuditService:
    def __init__(self, audit_repo: IAuditRepository, validator: IAuditValidator):
        self.audit_repo = audit_repo
        self.validator = validator

    def start_audit(self, request: StartAuditRequest) -> Result[AuditRun, str]:
        # Validation
        validation_result = self.validator.validate_request(request)
        if validation_result.is_failure():
            return failure(validation_result.error)

        # Business logic
        audit_run = AuditRun(
            organization=request.organization,
            config_hash=request.config_hash
        )

        # Persistence
        save_result = self.audit_repo.save(audit_run)
        if save_result.is_failure():
            return failure(f"Failed to save audit run: {save_result.error}")

        return success(save_result.value)
```

#### 1.2 Dependency Injection Container
```python
# src/autodbaudit/infrastructure/di/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # Infrastructure
    db_connection = providers.Singleton(ConnectionManager, db_path="audit.db")

    # Repositories
    audit_repo = providers.Factory(
        AuditRunRepository,
        connection_manager=db_connection
    )

    # Services
    audit_service = providers.Factory(
        AuditService,
        audit_repo=audit_repo,
        validator=providers.Factory(AuditValidator)
    )

    # Use cases / Application services
    start_audit_use_case = providers.Factory(
        StartAuditUseCase,
        audit_service=audit_service
    )
```

#### 1.3 Result Types (Railway-Oriented Programming)
```python
# src/autodbaudit/shared/result.py
from typing import Generic, TypeVar, Union

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Success(Generic[T]):
    value: T

@dataclass
class Failure(Generic[E]):
    error: E

Result = Union[Success[T], Failure[E]]

def success(value: T) -> Success[T]:
    return Success(value)

def failure(error: E) -> Failure[E]:
    return Failure(error)

# Extension methods
class ResultExtensions:
    @staticmethod
    def bind(result: Result[T, E], func) -> Result:
        """Monad bind operation for chaining operations"""
        if result.is_success():
            return func(result.value)
        return result

    @staticmethod
    def map(result: Result[T, E], func) -> Result:
        """Functor map operation"""
        if result.is_success():
            return success(func(result.value))
        return result
```

## Phase 2: Python Intermediate Concepts

### Goals
- Master decorators, context managers, type hints
- Implement async/await patterns
- Use protocols for dependency inversion
- Apply SOLID principles

### Key Implementations

#### 2.1 Context Managers for Resource Management
```python
# src/autodbaudit/infrastructure/sql/connection_manager.py
class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection = None

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            self._connection = pyodbc.connect(self.connection_string)
            yield self._connection
        finally:
            if self._connection:
                self._connection.close()

    async def execute_in_transaction(self, operation):
        """Async transaction management"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    conn.autocommit = False
                    result = await operation(cursor)
                    conn.commit()
                    return result
                except Exception:
                    conn.rollback()
                    raise
```

#### 2.2 Protocol-Based Dependency Inversion
```python
# src/autodbaudit/domain/ports.py
from typing import Protocol

class IAuditRepository(Protocol):
    def save(self, audit_run: AuditRun) -> Result[AuditRun, str]: ...

    def find_by_id(self, id: int) -> Result[AuditRun, str]: ...

class IAuditValidator(Protocol):
    def validate_request(self, request: StartAuditRequest) -> Result[None, str]: ...

# Implementation
class SqlAuditRepository:
    def save(self, audit_run: AuditRun) -> Result[AuditRun, str]:
        # Implementation using modern data access layer
        pass

# Usage with dependency injection
def create_audit_service(repo: IAuditRepository, validator: IAuditValidator) -> AuditService:
    return AuditService(repo, validator)
```

#### 2.3 Async/Await for I/O Operations
```python
# src/autodbaudit/application/use_cases/start_audit.py
class StartAuditUseCase:
    def __init__(self, audit_service: IAuditService):
        self.audit_service = audit_service

    async def execute(self, request: StartAuditRequest) -> Result[AuditRun, str]:
        # Validate input
        if not request.organization:
            return failure("Organization is required")

        # Start audit (potentially async I/O)
        result = await self.audit_service.start_audit_async(request)

        # Log result
        if result.is_success():
            await self._log_audit_started(result.value)

        return result

    async def _log_audit_started(self, audit_run: AuditRun):
        # Async logging operation
        pass
```

## Phase 3: Tooling Mastery

### Goals
- Implement comprehensive testing strategy
- Set up automated code quality
- Enable modern development workflow
- Achieve 95%+ test coverage

### Testing Strategy Implementation

#### 3.1 Multi-Layer Testing
```python
# tests/test_state_machine_comprehensive.py
class TestStateMachineComprehensive:
    def test_all_status_transitions(self):
        """Test all combinations of state transitions using combinatorial testing"""

        # Generate test cases with allpairspy
        parameters = {
            'old_status': [AuditStatus.PENDING, AuditStatus.RUNNING, AuditStatus.COMPLETED],
            'new_status': [AuditStatus.PENDING, AuditStatus.RUNNING, AuditStatus.COMPLETED, AuditStatus.FAILED],
            'has_exceptions': [False, True],
            'force_transition': [False, True]
        }

        test_cases = list(AllPairs(parameters))

        for case in test_cases:
            audit_run = AuditRun(status=case['old_status'])

            if case['force_transition']:
                # Test forced transitions (admin override)
                result = audit_run.force_transition_to(case['new_status'])
                assert result.is_success()
            else:
                # Test normal business rule transitions
                can_transition = audit_run.can_transition_to(case['new_status'])
                expected_success = self._should_allow_transition(
                    case['old_status'], case['new_status'], case['has_exceptions']
                )
                assert can_transition == expected_success

    def test_property_based_state_transitions(self):
        """Property-based testing with hypothesis"""
        @given(
            old_status=st.sampled_from(AuditStatus),
            new_status=st.sampled_from(AuditStatus),
            has_exceptions=st.booleans()
        )
        def test_transition_properties(old_status, new_status, has_exceptions):
            audit_run = AuditRun(status=old_status)

            # Property 1: Terminal states cannot transition
            if old_status in [AuditStatus.COMPLETED, AuditStatus.FAILED]:
                if not has_exceptions:  # Unless forced
                    assert not audit_run.can_transition_to(new_status)

            # Property 2: Valid transitions maintain invariants
            if audit_run.can_transition_to(new_status):
                audit_run.status = new_status
                assert audit_run.status == new_status
```

#### 3.2 Pre-commit Hooks Setup
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 2.1.2
    hooks:
      - id: sqlfluff-lint
        files: \.(sql)$
      - id: sqlfluff-fix
        files: \.(sql)$
```

## Phase 4: Fix Critical Issues

### Goals
- Address all pain points identified in analysis
- Implement modern data access patterns
- Fix SQL template management
- Improve error handling and logging

### Critical Fixes Implementation

#### 4.1 Modern Data Access Layer
```python
# src/autodbaudit/infrastructure/sqlite/modern_store.py
class ModernHistoryStore:
    """Modern SQLite store using repository pattern and result types"""

    def __init__(self, db_path: Path):
        self.conn_mgr = ConnectionManager(db_path)
        self.audit_repo = AuditRunRepository(self.conn_mgr, AuditRunModel)
        self.server_repo = ServerRepository(self.conn_mgr, ServerModel)
        self.instance_repo = InstanceRepository(self.conn_mgr, InstanceModel)

    async def begin_audit_run(self, organization: str | None = None) -> Result[AuditRunModel, str]:
        """Modern async audit run creation"""
        audit_run = AuditRunModel(
            organization=organization,
            status="running",
            started_at=datetime.now(timezone.utc)
        )

        result = await self.audit_repo.create(audit_run)
        if result.is_success():
            logger.info(f"Started audit run {result.value.id} for {organization}")
        return result

    async def get_audit_run(self, run_id: int) -> Result[AuditRunModel, str]:
        """Type-safe audit run retrieval"""
        return await self.audit_repo.get_by_id(run_id)
```

#### 4.2 SQL Template Management
```python
# src/autodbaudit/infrastructure/sql/template_manager.py
class SqlTemplateManager:
    """Modern SQL template management with validation"""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False  # SQL doesn't need HTML escaping
        )

        # Add custom filters
        self.env.filters['sql_escape'] = self._sql_escape

    def render_template(self, template_name: str, **context) -> str:
        """Render SQL template with context"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            raise ValueError(f"SQL template '{template_name}' not found")
        except TemplateSyntaxError as e:
            raise ValueError(f"SQL template syntax error: {e}")

    def validate_sql(self, sql: str) -> Result[str, str]:
        """Validate SQL syntax using sqlfluff"""
        try:
            # Use sqlfluff for validation
            result = sqlfluff.lint(sql, dialect='tsql')
            if result:
                errors = [f"Line {r['line_no']}: {r['description']}" for r in result]
                return failure("SQL validation errors: " + "; ".join(errors))
            return success(sql)
        except Exception as e:
            return failure(f"SQL validation failed: {str(e)}")

    def _sql_escape(self, value: str) -> str:
        """Custom Jinja filter for SQL escaping"""
        # Basic SQL escaping - in production, use proper parameterization
        return value.replace("'", "''")

# Usage
template_mgr = SqlTemplateManager(Path("src/autodbaudit/infrastructure/sql/templates"))

sql = template_mgr.render_template(
    "server_logins.sql",
    exclude_system_logins=True,
    database_name="master"
)

validated_sql = template_mgr.validate_sql(sql)
if validated_sql.is_success():
    results = connector.execute_query(validated_sql.value)
```

## Development Workflow

### Daily Development Cycle
1. **Feature Branch**: `git checkout -b feature/phase1-architecture`
2. **Pre-commit**: `pre-commit run --all-files` (catches issues early)
3. **Testing**: `pytest --cov=src --cov-report=html`
4. **Type Check**: `mypy src`
5. **SQL Lint**: `sqlfluff lint src/autodbaudit/infrastructure/sql/templates/`
6. **Commit**: `git commit -m "feat: implement domain models with business logic"`

### CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]
      - name: Run pre-commit
        run: pre-commit run --all-files
      - name: Run tests with coverage
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Performance Benchmarks
```python
# tests/benchmark_data_access.py
import pytest_benchmark

@pytest.mark.benchmark
def test_audit_run_creation_performance(benchmark):
    """Benchmark audit run creation performance"""

    def create_audit_runs():
        store = ModernHistoryStore(Path(":memory:"))
        for i in range(100):
            result = asyncio.run(store.begin_audit_run(f"Org{i}"))
            assert result.is_success()

    benchmark(create_audit_runs)
```

## Success Metrics

### Phase 1 Completion
- [ ] Domain models with business logic implemented
- [ ] Dependency injection container configured
- [ ] Result types used throughout application
- [ ] Clean architecture layers established

### Phase 2 Completion
- [ ] All intermediate Python concepts demonstrated
- [ ] Async/await used for I/O operations
- [ ] Protocol-based design implemented
- [ ] SOLID principles applied

### Phase 3 Completion
- [ ] 95%+ test coverage achieved
- [ ] Pre-commit hooks passing
- [ ] CI/CD pipeline operational
- [ ] Performance benchmarks established

### Phase 4 Completion
- [ ] All critical issues resolved
- [ ] Modern data access layer fully implemented
- [ ] SQL templates externalized and validated
- [ ] Error handling comprehensive

## Next Steps

1. **Start Phase 1**: Begin with domain modeling and dependency injection
2. **Daily Practice**: Implement one concept per day with tests
3. **Weekly Review**: Assess progress and adjust approach
4. **Monthly Milestone**: Complete one phase per month

This systematic approach will transform your codebase into a modern, maintainable, and robust system while teaching advanced Python concepts and architecture patterns.