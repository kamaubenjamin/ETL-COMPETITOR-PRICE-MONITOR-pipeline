# Phase 3+: Declarative Workflow Architecture

## Overview
Evolved from hardcoded workflow logic to portable, declarative JSON-based workflow definitions with a universal orchestration engine. This enables:
- **Reusable workflows** without code changes
- **Configurable execution pipelines** per workflow
- **Centralized workflow management** via JSON files
- **Scalable architecture** supporting unlimited workflows
- **Audit trail** of workflow executions

## Architecture Components

### 1. Workflow Definitions (`workflows/` directory)

**Purpose**: Store declarative workflow configurations as JSON files

**Location**: `workflows/*.json`

**Structure**:
```json
{
  "workflow_id": "electronics_monitoring",
  "workflow_name": "Electronics Price Monitoring",
  "description": "Monitor competitor pricing...",
  "enabled": true,
  
  "sources": [
    {
      "name": "jumia_electronics",
      "source_type": "playwright",
      "url": "https://www.jumia.co.ke/electronics/",
      "selector": "article.prd",
      "keyword": "electronics",
      "match_threshold": 72
    }
  ],
  
  "filters": {
    "category": "electronics",
    "keywords": ["tv", "smart tv", "monitor"]
  },
  
  "transformation_rules": [
    {"type": "drop_nulls", "subset": ["price"]},
    {"type": "filter", "condition": "price > 5000"}
  ],
  
  "steps": [
    "extract",
    "normalize",
    "fuzzy_match",
    "compare",
    "detect_changes",
    "generate_alerts",
    "generate_reports"
  ],
  
  "alert_rules": {
    "price_drop_percentage": 5,
    "price_drop_absolute": 1000,
    "minimum_confidence": 0.75,
    "undercut_threshold": 2000
  },
  
  "schedule": {
    "frequency": "daily",
    "time_of_day": "08:00",
    "day_of_week": null,
    "enabled": true
  },
  
  "reporting": {
    "export_csv": true,
    "export_pdf": true,
    "report_dir": "reports"
  },
  
  "global_match_threshold": 70
}
```

**Key Fields**:
- `workflow_id`: Unique identifier for the workflow
- `sources`: Data sources to extract from (Jumia, Kilimall, etc.)
- `filters`: Optional filtering by category/keywords
- `transformation_rules`: Data cleaning and transformation rules
- `steps`: Execution pipeline (extract → normalize → match → compare → alerts → reports)
- `alert_rules`: Conditions for generating price alerts
- `schedule`: Automated execution schedule (frequency, time, day)
- `reporting`: Output format configuration (CSV, PDF)

### 2. Workflow Runner (`src/workflow_runner.py`)

**Purpose**: Universal orchestration engine that loads and executes workflow definitions

**Key Classes**:
```python
class WorkflowRunner:
    def load_workflows()          # Load all JSON definitions
    def get_workflow()            # Retrieve workflow by ID
    def workflow_to_config()      # Convert JSON to WorkflowConfig
    def execute_workflow()        # Execute complete workflow pipeline
    def execute_due_workflows()   # Run all workflows due to run
    def get_execution_history()   # View past executions
```

**Execution Flow**:
```
load_workflows()
  ↓
workflow_to_config()
  ↓
execute_workflow()
  ├─ extract (multi-source data ingestion)
  ├─ normalize (product standardization)
  ├─ fuzzy_match (intelligent deduplication)
  ├─ compare (cross-source pricing)
  ├─ detect_changes (identify price movements)
  ├─ generate_alerts (trigger notifications)
  └─ generate_reports (CSV/PDF export)
  ↓
record_execution()
```

### 3. Integration Points

**Dashboard Integration**:
- Load workflows from `WorkflowRunner.list_workflows()`
- Display in workflow selector dropdown
- Run on-demand via "Run Workflow" button
- Auto-execute due workflows on app startup

**Scheduler Integration**:
- Create schedules from workflow `schedule` field
- Auto-populate with frequency, time, day
- Track next-run times
- Record execution history

**Reporter Integration**:
- Use workflow `reporting` config
- Generate timestamped CSV exports
- Generate PDF reports if enabled
- Store in workflow-specific directories

## Files Created/Modified

| File | Status | Purpose |
|------|--------|---------|
| `workflows/electronics_monitoring.json` | NEW | Example electronics monitoring workflow |
| `workflows/smartphones_monitoring.json` | NEW | Example smartphone monitoring workflow |
| `src/workflow_runner.py` | NEW | Universal workflow orchestration engine |
| `demo_workflow_runner.py` | NEW | Demonstration of workflow system |
| `test_workflow_runner.py` | NEW | Test suite for workflow runner |

## Testing & Validation

### Test Suite: `test_workflow_runner.py`

**Coverage**:
1. ✅ Workflow file loading from disk
2. ✅ Workflow retrieval and structure validation
3. ✅ JSON-to-WorkflowConfig conversion
4. ✅ Source configuration parsing
5. ✅ Workflow registration to global registry
6. ✅ Schedule creation from workflow definitions
7. ✅ Alert rules configuration
8. ✅ Reporting configuration

**Results**: **10/10 tests PASSED**

### Demo: `demo_workflow_runner.py`

Shows:
- Loading 2 workflows from JSON
- Converting to WorkflowConfig objects
- Registering to global registry
- Creating schedules with next-run times
- Displaying workflow execution steps

## Usage Examples

### Loading Workflows
```python
from src.workflow_runner import runner

# List all available workflows
workflows = runner.list_workflows()
# ['electronics_monitoring', 'smartphones_monitoring']

# Load a specific workflow
workflow_def = runner.get_workflow("electronics_monitoring")
```

### Converting to Config
```python
# Convert JSON definition to WorkflowConfig
config = runner.workflow_to_config(workflow_def)
# Usable with existing pipeline functions
```

### Executing Workflows
```python
# Execute a complete workflow pipeline
result = runner.execute_workflow("electronics_monitoring")

# Result contains:
# - execution_log with timestamps
# - step-by-step execution details
# - generated reports and alerts
# - execution history
```

### Creating Schedules from Workflows
```python
# Automatically schedule workflows from definitions
from src.scheduler import scheduler

for workflow_id in runner.list_workflows():
    workflow_def = runner.get_workflow(workflow_id)
    schedule_def = workflow_def.get("schedule", {})
    
    if schedule_def.get("enabled"):
        scheduler.create_schedule(
            workflow_id=workflow_id,
            frequency=schedule_def.get("frequency"),
            time_of_day=schedule_def.get("time_of_day")
        )
```

## Architecture Benefits

### Before (Hardcoded)
```
Dashboard UI
    ↓
Python Code (ETL Pipeline)
    ↓
Database/CSV
```
- Workflows embedded in Python code
- Changes require code editing and deployment
- Limited reusability across projects
- Tight coupling between UI and logic

### After (Declarative + Runner)
```
Workflow JSON Definitions
    ↓
Workflow Runner (Universal Orchestrator)
    ↓
Pipeline Execution
    ↓
Reporting + Scheduling
```
- Workflows defined as portable JSON configs
- Changes via config editing (no code deploy)
- Reusable across multiple environments
- Loose coupling enables scalability

## Next Steps

1. **Dashboard Integration**: Update `dashboard.py` to use `WorkflowRunner` instead of hardcoded workflow logic
2. **Workflow Builder UI**: Add visual workflow editor to dashboard
3. **Workflow Marketplace**: Share/import workflows from community repos
4. **Advanced Orchestration**: Add conditional logic, parallel execution, error handling
5. **Workflow Versioning**: Track workflow definition changes over time

## Key Files Location

- **Workflow Definitions**: `workflows/*.json`
- **Orchestrator**: `src/workflow_runner.py`
- **Tests**: `test_workflow_runner.py`
- **Demo**: `demo_workflow_runner.py`

## Current State

✅ **Complete Implementation**
- 2 example workflows with full definitions
- Universal workflow runner engine
- Integration with scheduler and reporter
- Comprehensive test coverage (10/10 tests passing)
- Demonstration script showing all capabilities

🎯 **Key Achievement**: Workflows are now declarative, portable, and scalable without code changes.
