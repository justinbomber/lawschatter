# Coding Style Guide

## Core Principles

### 1. Modular Design
- **Complete Separation**: Every functionality must be in its own module
- **Single Responsibility**: Each module handles one specific concern
- **Clean Interfaces**: Clear, simple APIs between modules
- **No Cross-Dependencies**: Modules should not directly depend on each other except through well-defined interfaces

### 2. Error Handling Philosophy
- **No Try-Catch**: Absolutely no exception handling mechanisms
- **Fail Fast**: Let errors bubble up immediately
- **Fix Later**: Address errors through debugging, not defensive programming
- **Direct Failure**: Errors should crash the program with clear stack traces

### 3. Logging Standards
- **Minimal Logging**: Only log essential information
- **No Emojis**: Strict text-only logging
- **Verbosity Levels**: Respect logging level configurations
- **Simple Format**: `%(asctime)s | %(levelname)s | %(message)s`
- **Purpose-Driven**: Log only actionable information

### 4. Code Simplicity
- **Minimal Code**: Write only what is necessary
- **No Test Code**: Production code only, no testing scaffolding
- **Direct Implementation**: Solve the problem directly without abstractions
- **Clear Intent**: Code should be self-documenting

## Implementation Patterns

### Module Structure
```
src/
├── modules/
│   ├── __init__.py
│   ├── config.py      # Configuration management
│   ├── database.py    # Data persistence layer
│   ├── handler.py     # Business logic
│   └── parser.py      # Data processing
└── api/
    ├── __init__.py
    └── main.py        # API endpoints
```

### Configuration Pattern
```python
@dataclass
class Config:
    required_field: str
    optional_field: str = "default"

    @classmethod
    def from_env(cls):
        return cls(
            required_field=os.getenv('REQUIRED_FIELD'),
            optional_field=os.getenv('OPTIONAL_FIELD', cls.optional_field)
        )

    def validate(self):
        if not self.required_field:
            raise EnvironmentError("REQUIRED_FIELD environment variable is required")
```

### Database Connection Pattern
```python
class DatabaseConnection:
    def __init__(self, config: Config):
        self.config = config
        self.client = create_client(config.url, config.key)

    def insert_data(self, data: dict):
        table_name = f"{self.config.schema}.{self.config.table}"
        result = self.client.table(table_name).insert(data).execute()
        return result
```

### Business Logic Pattern
```python
class BusinessLogic:
    def __init__(self, dependencies):
        self.dependency = dependencies

    def process(self, input_data):
        # Direct processing without error handling
        result = self.dependency.method(input_data)
        return result
```

### API Pattern
```python
from fastapi import FastAPI, UploadFile, File
from ..modules.config import Config
from ..modules.handler import Handler

app = FastAPI(title="Service Name")
config = Config.from_env()
config.validate()
handler = Handler(config)

@app.post("/endpoint")
async def endpoint(file: UploadFile = File(...)):
    result = handler.process(file)
    return {"result": result}
```

## File Organization

### Environment Configuration
- `.env`: Actual environment variables
- `.env.example`: Template with placeholder values
- Environment variables always in UPPER_CASE

### Dependencies
- `requirements.txt`: Exact version pins
- Minimal dependencies only
- No development or testing dependencies

### Documentation
- `README.md`: Basic setup and usage only
- No extensive documentation
- Code should be self-explanatory

## Naming Conventions

### Variables and Functions
- `snake_case` for all Python identifiers
- Descriptive but concise names
- No abbreviations unless universally understood

### Classes
- `PascalCase` for class names
- Noun-based names describing the entity
- Clear, single-concept classes

### Files and Directories
- `snake_case` for file names
- Descriptive module names
- Clear directory structure

## Anti-Patterns to Avoid

### Error Handling
- ❌ `try/except` blocks
- ❌ Error recovery mechanisms
- ❌ Defensive programming
- ❌ Silent error suppression

### Logging
- ❌ Emoji or special characters
- ❌ Verbose debugging information
- ❌ Multiple logging frameworks
- ❌ Complex log formatting

### Code Structure
- ❌ Monolithic functions
- ❌ Tight coupling between modules
- ❌ Multiple responsibilities in one class
- ❌ Unnecessary abstractions

### Development Artifacts
- ❌ Test code in production modules
- ❌ Debug print statements
- ❌ Commented-out code
- ❌ Development-only dependencies

## Environment Standards

### Required Environment Variables
Always validate required environment variables on startup:
```python
def validate(self):
    if not self.required_var:
        raise EnvironmentError("REQUIRED_VAR environment variable is required")
```

### Logging Setup
Standard logging configuration:
```python
def setup_logging(self):
    logging.basicConfig(
        level=self.log_level,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    return logging.getLogger("service_name")
```

### Application Startup
Clean, minimal startup sequence:
```python
if __name__ == "__main__":
    config = Config.from_env()
    config.validate()
    logger = config.setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

This style emphasizes clarity, simplicity, and direct problem-solving while maintaining clean architecture principles.