---
mode: edit
---
# Integration Test Guidelines

You are tasked with writing comprehensive integration tests following established patterns in the codebase. Follow these exact requirements and conventions.

## Core Principles

### 1. Test Behavior, Not Implementation
- Integration tests verify that components work correctly together
- Test the observable behavior and outcomes, not internal implementation details
- Focus on what the code does, not how it does it
- Avoid testing private methods or internal state unless necessary

### 2. Layer-Specific Testing
- **Endpoint tests** test only the HTTP layer:
  - Request/response handling
  - Authentication and authorization
  - HTTP status codes
  - Request body parsing
  - Do NOT test the underlying API logic - that's the API's job
- **API tests** test only the business logic layer:
  - Business rules and validation
  - Data transformations
  - Error handling
  - Return values and data structures
  - Do NOT test database operations - mock them

### 3. Use Fixtures Exclusively
- **NEVER** define test data directly in test functions
- **ALWAYS** create fixtures for any temporary variables
- Follow the patterns in `integrations/auth/fixtures.py`
- Use appropriate scopes:
  - `scope='session'` for immutable test data
  - `scope='function'` for database objects or mutable state

## File Organization

### Directory Structure
```
integrations/
├── fixtures.py                    # Base fixtures (state, session, test_app)
├── auth/
│   ├── fixtures.py               # Auth-specific fixtures
│   ├── test_auth_api.py          # Auth API layer tests
│   └── test_auth_endpoints.py    # Auth endpoint layer tests
└── server_ops/
    └── arma/
        ├── fixtures.py           # Arma-specific fixtures
        ├── test_arma_api.py      # Arma API layer tests
        └── test_arma_endpoints.py # Arma endpoint layer tests
```

### Fixture Files
Each module should have its own `fixtures.py` with:
1. Session-scoped fixtures for immutable test data
2. Function-scoped fixtures for database objects
3. Fixtures that compose other fixtures
4. Clear, descriptive fixture names

## Fixture Patterns

### Session-Scoped Fixtures (Immutable Data)
Use for constants, configuration values, test data that never changes:

```python
@pytest.fixture(scope='session')
def token_1():
    return 'token 1'

@pytest.fixture(scope='session')
def mock_mod_name_1():
    return 'mod1'

@pytest.fixture(scope='session')
def endpoint_mods_url():
    return '/api/v1/server_ops/arma/mods'
```

### Composite Session Fixtures
Build complex objects from simpler fixtures:

```python
@pytest.fixture(scope='session')
def mock_mod_1(mock_mod_name_1, mock_workshop_id_1):
    return Mod(name=mock_mod_name_1, workshop_id=WorkshopId(mock_workshop_id_1))

@pytest.fixture(scope='session')
def role_1() -> Roles:
    return Roles(can_create_group=False, can_create_role=True, can_manage_server=False)
```

### Function-Scoped Fixtures (Database Objects)
Use for objects that interact with the database:

```python
@pytest.fixture(scope='function')
def db_user_1(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=1).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user

@pytest.fixture(scope='function')
def db_mod_1(state, session, workshop_details_1):
    with state.Session.begin() as session:
        db_mod = DbMod.from_workshop_details(workshop_details_1)
        session.add(db_mod)
        session.flush()
        session.expunge(db_mod)
    yield db_mod
```

### Endpoint URL Fixtures
Create a hierarchy of URL fixtures:

```python
@pytest.fixture(scope='session')
def endpoint_api_url():
    return '/api'

@pytest.fixture(scope='session')
def endpoint_api_v1_url(endpoint_api_url):
    return f'{endpoint_api_url}/v1'

@pytest.fixture(scope='session')
def endpoint_user_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/user/'
```

## Test Structure

### Test Function Naming
- Use descriptive, behavior-focused names
- Format: `test__<method_name>__<behavior_description>`
- Examples:
  - `test__get_all_configured_mods__returns_all_mods`
  - `test__add_new_mod__raises_when_mod_already_exists`
  - `test__reload_mods__requires_authentication`

### Test Function Signature
List ALL fixtures used in the test as parameters:

```python
def test__get_all_configured_mods__returns_all_mods(
    mocker,           # From pytest-mock
    state,            # From integrations.fixtures
    session,          # From integrations.fixtures
    mock_mod_1,       # From module fixtures
    mock_mod_2        # From module fixtures
):
    """Test that get_all_configured_mods returns all configured mods"""
    # Not yet reviewed
    # Test implementation
```

### Docstrings
Every test should have a clear docstring explaining what it tests:

```python
def test__add_new_mod__requires_authentication(state, session, test_app, endpoint_mods_url):
    """Test that POST /mods requires authentication"""
    # Not yet reviewed
    # Test implementation
```

### Review Status Comment
**REQUIRED**: Every test function must include a `# Not yet reviewed` comment immediately after the docstring. This indicates that a human has not yet reviewed the test. Once reviewed, this comment should be removed or replaced with `# Reviewed: <date>`.

```python
def test__example(state, session):
    """Test description"""
    # Not yet reviewed
    # Test implementation
```

This helps track which tests have been manually verified by a human reviewer.

## API Test Patterns

### Good API Test Example
```python
def test__create_new_user_bot__can_create_and_get_token(mocker, state, session, token_1):
    """Test that create_new_user_bot creates a bot user and returns token"""
    # Not yet reviewed
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    
    response = AuthApi().create_new_user_bot(state)
    
    assert response.status_code == 201
    assert response.contained_json['bot_token'] == token_1
```

### What API Tests Should Cover
- ✅ Successful operations
- ✅ Error conditions (missing data, invalid data)
- ✅ Return values and data structures
- ✅ Business logic validation
- ✅ Exception handling

### What API Tests Should NOT Cover
- ❌ HTTP request/response details (that's for endpoint tests)
- ❌ Database internals (mock database operations)
- ❌ Authentication decorators (that's for endpoint tests)

## Endpoint Test Patterns

### Good Endpoint Test Example
```python
@pytest.mark.asyncio
async def test__create_role__role_created(
    state, 
    session, 
    test_app, 
    db_user_1, 
    role_1, 
    db_session_1, 
    db_role_assigner, 
    endpoint_user_role_create_url
):
    """Test that POST /user/role/create creates a new role"""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)
    
    response = await test_app.post(
        endpoint_user_role_create_url,
        json={'role_name': 'test_role', **role_1.as_dict()},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    
    assert response.status_code == 201
    data = await response.get_json()
    assert data['name'] == 'test_role'
```

### What Endpoint Tests Should Cover
- ✅ HTTP status codes for success and errors
- ✅ Authentication requirements (401 when not authenticated)
- ✅ Authorization requirements (403 when lacking permissions)
- ✅ Expired session handling
- ✅ Request body parsing
- ✅ Response format (JSON structure)
- ✅ Path parameter handling

### What Endpoint Tests Should NOT Cover
- ❌ Business logic details (that's for API tests)
- ❌ Database operations (trust the API layer)
- ❌ Complex validation logic (test at API layer)

### Common Endpoint Test Scenarios

#### 1. Success Case
```python
@pytest.mark.asyncio
async def test__<endpoint>__<action>_successfully(
    state, session, test_app, db_user_1, db_session_1, can_manage_server_role, endpoint_url
):
    """Test that endpoint performs action successfully"""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, can_manage_server_role.name)
    
    response = await test_app.post(
        endpoint_url,
        json={...},
        headers={'Authorization': f'Bearer {db_session_1.token}'}
    )
    
    assert response.status_code == 200  # or 201
```

#### 2. Requires Authentication
```python
@pytest.mark.asyncio
async def test__<endpoint>__requires_authentication(state, session, test_app, endpoint_url):
    """Test that endpoint requires authentication"""
    # Not yet reviewed
    response = await test_app.post(endpoint_url, json={...})
    
    assert response.status_code == 401
```

#### 3. Requires Permission
```python
@pytest.mark.asyncio
async def test__<endpoint>__requires_permission(
    state, session, test_app, db_user_1, db_session_1, endpoint_url
):
    """Test that endpoint requires specific role/permission"""
    # Not yet reviewed
    response = await test_app.post(
        endpoint_url,
        json={...},
        headers={'Authorization': f'Bearer {db_session_1.token}'}
    )
    
    assert response.status_code == 403
```

#### 4. Expired Session
```python
@pytest.mark.asyncio
async def test__<endpoint>__rejects_expired_session(
    mocker, state, session, test_app, db_user_1, db_expired_session_1, can_manage_server_role, endpoint_url
):
    """Test that endpoint rejects expired sessions"""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, can_manage_server_role.name)
    
    response = await test_app.post(
        endpoint_url,
        json={...},
        headers={'Authorization': f'Bearer {db_expired_session_1.token}'}
    )
    
    assert response.status_code == 401
```

## Test Coverage Requirements

### Minimum Coverage Per API Method
For each API method, create tests for:
1. Success case
2. Each error condition (not found, already exists, invalid input, etc.)
3. Edge cases (empty input, null values, etc.)

### Minimum Coverage Per Endpoint
For each endpoint, create tests for:
1. Success case
2. Requires authentication (if protected)
3. Requires permission (if role-protected)
4. Expired session (if session-protected)
5. Invalid input (if accepting data)
6. Not found (if referencing resources)

### Example Complete Coverage
```python
# API Tests (5 tests)
def test__add_mod__successfully_adds_new_mod(...)
def test__add_mod__raises_when_mod_already_exists(...)
def test__add_mod__raises_when_workshop_id_missing_for_non_manual(...)
def test__add_mod__raises_when_invalid_kind(...)
def test__add_mod__raises_when_duplicate_workshop_id(...)

# Endpoint Tests (5 tests)
async def test__add_new_mod__creates_mod_successfully(...)
async def test__add_new_mod__requires_authentication(...)
async def test__add_new_mod__requires_permission(...)
async def test__add_new_mod__rejects_duplicate_mod(...)
async def test__add_new_mod__rejects_invalid_kind(...)
```

## Common Patterns

### Mocking
Use `mocker` fixture from pytest-mock:

```python
def test__example(mocker, state, session):
    """Test description"""
    # Not yet reviewed
    # Mock external dependencies
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mock_func = mocker.patch('module.function', return_value='value')
    
    # Test implementation
    
    # Verify mocks were called
    mock_func.assert_called_once_with('expected_arg')
```

### Async Tests
All endpoint tests must be async:

```python
@pytest.mark.asyncio
async def test__endpoint_name(test_app, endpoint_url):
    """Test description"""
    # Not yet reviewed
    response = await test_app.get(endpoint_url)
    assert response.status_code == 200
```

## Import Patterns

### Standard Test Imports
```python
# ruff: noqa: F811, F401

import pytest

from integrations.fixtures import test_app, session, state
from integrations.auth.fixtures import (
    db_user_1,
    db_session_1,
    db_expired_session_1,
)
from integrations.module.fixtures import (
    # Module-specific fixtures
)
from bw.module.api import ModuleApi
from bw.auth.user import UserStore
```

### Fixture Import Rules
- Import base fixtures from `integrations.fixtures`
- Import auth fixtures from `integrations.auth.fixtures`
- Import module fixtures from `integrations.module.fixtures`
- Import only the fixtures you use
- Use `# ruff: noqa: F811, F401` to suppress unused import warnings

## Naming Conventions

### Fixture Names
- Use descriptive names: `db_user_1`, `mock_mod_1`, `workshop_details_1`
- Number similar fixtures: `token_1`, `token_2`, `token_3`
- Prefix database fixtures with `db_`: `db_user_1`, `db_session_1`
- Prefix mock objects with `mock_`: `mock_mod_1`, `mock_server`
- Use semantic names for URLs: `endpoint_mods_url`, `endpoint_user_role_create_url`

### Test Names
- Format: `test__<function>__<behavior>`
- Use snake_case
- Be descriptive and specific
- Examples:
  - `test__get_all_configured_mods__returns_all_mods`
  - `test__add_new_mod__raises_when_mod_already_exists`

## Quality Checklist

Before submitting tests, verify:
- [ ] All temporary variables are in fixtures
- [ ] Test names clearly describe behavior
- [ ] Each test has a docstring
- [ ] Each test has `# Not yet reviewed` comment after docstring
- [ ] Tests use appropriate fixtures from the fixtures file
- [ ] API tests only test business logic
- [ ] Endpoint tests only test HTTP layer
- [ ] All success and error cases are covered
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] Imports follow the standard pattern
- [ ] No hardcoded test data in test functions
- [ ] Mocks are properly configured and verified
- [ ] Tests are focused and test one thing

## Anti-Patterns to Avoid

### ❌ Bad: Hardcoded test data
```python
def test__example(state, session):
    """Test description"""
    # Not yet reviewed
    mock_mods = {
        'mod1': Mod(name='mod1', workshop_id=WorkshopId(123)),
    }
```

### ✅ Good: Use fixtures
```python
def test__example(state, session, mock_mod_1):
    """Test description"""
    # Not yet reviewed
    mock_mods = {mock_mod_1.name: mock_mod_1}
```

### ❌ Bad: Testing implementation details
```python
def test__api_method__uses_correct_database_query(state, session):
    """Don't test internal database queries"""
    # Not yet reviewed
    # Don't test internal database queries
```

### ✅ Good: Testing behavior
```python
def test__api_method__returns_correct_data(state, session):
    """Test what the method returns"""
    # Not yet reviewed
    # Test what the method returns
```

### ❌ Bad: Endpoint test checking business logic
```python
async def test__endpoint__validates_workshop_id(test_app):
    """Don't test validation logic in endpoint tests"""
    # Not yet reviewed
    # Don't test validation logic in endpoint tests
```

### ✅ Good: Endpoint test checking HTTP behavior
```python
async def test__endpoint__returns_400_for_invalid_input(test_app):
    """Test HTTP response, not the validation details"""
    # Not yet reviewed
    # Test HTTP response, not the validation details
```

## Reference Examples

For complete reference implementations, see:
- `integrations/auth/fixtures.py` - Fixture patterns
- `integrations/auth/test_auth_api.py` - API test patterns
- `integrations/auth/test_auth_endpoints.py` - Endpoint test patterns
- `integrations/server_ops/arma/fixtures.py` - Module-specific fixtures
- `integrations/server_ops/arma/test_arma_api.py` - Module API tests
- `integrations/server_ops/arma/test_arma_endpoints.py` - Module endpoint tests

## Summary

Remember:
1. **Use fixtures exclusively** - no hardcoded test data
2. **Test behavior** - not implementation details
3. **Separate concerns** - API tests vs endpoint tests
4. **Follow patterns** - consistency is key
5. **Comprehensive coverage** - success and error cases
6. **Clear naming** - descriptive and consistent
