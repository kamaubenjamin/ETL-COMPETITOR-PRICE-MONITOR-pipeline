"""
Test suite for the workflow runner - validates workflow loading, config conversion, and scheduling.
"""
import os
import json
from src.workflow_runner import runner
from src.scheduler import scheduler


def test_load_workflows():
    """Test that workflows are loaded from JSON files."""
    print("\n✅ Testing workflow loading...")
    workflows = runner.list_workflows()
    assert len(workflows) >= 2, f"Expected at least 2 workflows, got {len(workflows)}"
    assert "electronics_monitoring" in workflows, "electronics_monitoring workflow not found"
    assert "smartphones_monitoring" in workflows, "smartphones_monitoring workflow not found"
    print(f"   ✓ Found {len(workflows)} workflows")


def test_get_workflow():
    """Test retrieving a workflow definition."""
    print("\n✅ Testing workflow retrieval...")
    workflow = runner.get_workflow("electronics_monitoring")
    assert workflow is not None, "Failed to retrieve electronics_monitoring workflow"
    assert workflow["workflow_id"] == "electronics_monitoring"
    assert "sources" in workflow
    assert len(workflow["sources"]) == 2
    print("   ✓ Successfully retrieved workflow definition")


def test_workflow_structure():
    """Test that workflow definitions have required fields."""
    print("\n✅ Testing workflow structure...")
    for workflow_id in runner.list_workflows():
        workflow = runner.get_workflow(workflow_id)
        assert "workflow_id" in workflow, f"Missing workflow_id in {workflow_id}"
        assert "workflow_name" in workflow, f"Missing workflow_name in {workflow_id}"
        assert "sources" in workflow, f"Missing sources in {workflow_id}"
        assert "steps" in workflow, f"Missing steps in {workflow_id}"
        assert "schedule" in workflow, f"Missing schedule in {workflow_id}"
        assert "alert_rules" in workflow, f"Missing alert_rules in {workflow_id}"
        print(f"   ✓ {workflow_id} has all required fields")


def test_workflow_to_config():
    """Test converting workflow definition to WorkflowConfig."""
    print("\n✅ Testing workflow-to-config conversion...")
    workflow_def = runner.get_workflow("electronics_monitoring")
    config = runner.workflow_to_config(workflow_def)
    
    assert config.workflow_id == "electronics_monitoring"
    assert config.name == "Electronics Price Monitoring"
    assert len(config.sources) == 2
    assert config.global_match_threshold == 70
    print("   ✓ Successfully converted workflow definition to WorkflowConfig")


def test_source_conversion():
    """Test that sources are correctly converted from workflow definition."""
    print("\n✅ Testing source conversion...")
    workflow_def = runner.get_workflow("electronics_monitoring")
    config = runner.workflow_to_config(workflow_def)
    
    sources = config.sources
    assert len(sources) == 2
    assert sources[0].name == "jumia_electronics"
    assert sources[0].source_type == "playwright"
    assert sources[0].url == "https://www.jumia.co.ke/electronics/"
    assert sources[0].selector == "article.prd"
    print("   ✓ Sources correctly converted from workflow definition")


def test_workflow_registration():
    """Test registering workflows to global registry."""
    print("\n✅ Testing workflow registration...")
    success = runner.register_workflow_to_registry("electronics_monitoring")
    assert success, "Failed to register workflow"
    print("   ✓ Successfully registered workflow to global registry")


def test_schedule_creation():
    """Test creating schedules from workflow definitions."""
    print("\n✅ Testing schedule creation...")
    
    # Clear existing schedules first
    for sched in scheduler.list_schedules():
        scheduler.delete_schedule(sched.workflow_id)
    
    for workflow_id in runner.list_workflows():
        workflow_def = runner.get_workflow(workflow_id)
        schedule_def = workflow_def.get("schedule", {})
        
        if schedule_def.get("enabled"):
            schedule = scheduler.create_schedule(
                workflow_id=workflow_id,
                frequency=schedule_def.get("frequency", "manual"),
                time_of_day=schedule_def.get("time_of_day"),
                day_of_week=schedule_def.get("day_of_week"),
            )
            assert schedule is not None, f"Failed to create schedule for {workflow_id}"
            assert schedule.workflow_id == workflow_id
            assert schedule.frequency == schedule_def.get("frequency")
            print(f"   ✓ Created schedule for {workflow_id}")


def test_alert_rules():
    """Test that alert rules are properly loaded from workflow definition."""
    print("\n✅ Testing alert rules...")
    workflow_def = runner.get_workflow("electronics_monitoring")
    alert_rules = workflow_def.get("alert_rules", {})
    
    assert "price_drop_percentage" in alert_rules
    assert "minimum_confidence" in alert_rules
    assert alert_rules["price_drop_percentage"] == 5
    assert alert_rules["minimum_confidence"] == 0.75
    print("   ✓ Alert rules properly configured")


def test_reporting_config():
    """Test that reporting configuration is present in workflow definition."""
    print("\n✅ Testing reporting configuration...")
    workflow_def = runner.get_workflow("electronics_monitoring")
    reporting = workflow_def.get("reporting", {})
    
    assert "export_csv" in reporting
    assert "export_pdf" in reporting
    assert reporting["export_csv"] is True
    assert reporting["export_pdf"] is True
    print("   ✓ Reporting configuration is valid")


def test_workflow_files_exist():
    """Test that workflow JSON files actually exist on disk."""
    print("\n✅ Testing workflow files existence...")
    workflows_dir = "workflows"
    assert os.path.isdir(workflows_dir), f"Workflows directory not found at {workflows_dir}"
    
    files = os.listdir(workflows_dir)
    json_files = [f for f in files if f.endswith(".json")]
    assert len(json_files) >= 2, f"Expected at least 2 JSON files, found {len(json_files)}"
    print(f"   ✓ Found {len(json_files)} workflow JSON files")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 WORKFLOW RUNNER TEST SUITE")
    print("="*70)

    tests = [
        test_workflow_files_exist,
        test_load_workflows,
        test_get_workflow,
        test_workflow_structure,
        test_workflow_to_config,
        test_source_conversion,
        test_workflow_registration,
        test_schedule_creation,
        test_alert_rules,
        test_reporting_config,
    ]

    failed = []
    passed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"   ✗ {test.__name__} failed: {e}")
            failed.append((test.__name__, str(e)))
        except Exception as e:
            print(f"   ✗ {test.__name__} error: {e}")
            failed.append((test.__name__, str(e)))

    print("\n" + "="*70)
    print(f"✅ RESULTS: {passed} passed, {len(failed)} failed")
    print("="*70)

    if failed:
        print("\n❌ Failed tests:")
        for test_name, error in failed:
            print(f"  • {test_name}: {error}")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
