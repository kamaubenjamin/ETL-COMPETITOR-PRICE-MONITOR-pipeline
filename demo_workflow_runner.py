"""
Demonstration of the declarative workflow runner.
Shows how workflows are loaded from JSON and executed end-to-end.
"""
import os
import json
from src.workflow_runner import runner
from src.scheduler import scheduler


def demo_load_workflows():
    """Demonstrate loading workflows from JSON definitions."""
    print("\n" + "="*70)
    print("📂 LOADING WORKFLOWS FROM JSON DEFINITIONS")
    print("="*70)

    available = runner.list_workflows()
    print(f"\n✅ Found {len(available)} workflows:")
    for wid in available:
        workflow = runner.get_workflow(wid)
        print(f"  • {wid}")
        print(f"    Name: {workflow.get('workflow_name')}")
        print(f"    Sources: {len(workflow.get('sources', []))}")
        print(f"    Steps: {', '.join(workflow.get('steps', []))}")
        print()


def demo_workflow_config_conversion():
    """Demonstrate converting workflow definitions to configs."""
    print("\n" + "="*70)
    print("🔄 CONVERTING WORKFLOW DEFINITIONS TO CONFIGS")
    print("="*70)

    workflow_def = runner.get_workflow("electronics_monitoring")
    config = runner.workflow_to_config(workflow_def)

    print(f"\n✅ Converted 'electronics_monitoring' to WorkflowConfig:")
    print(f"  Workflow ID: {config.workflow_id}")
    print(f"  Name: {config.name}")
    print(f"  Sources: {len(config.sources)}")
    for source in config.sources:
        print(f"    • {source.name} ({source.source_type})")
    print(f"  Global Match Threshold: {config.global_match_threshold}")
    print(f"  Alert Rules: {config.alert_rules}")


def demo_workflow_registration():
    """Demonstrate registering workflows to the global registry."""
    print("\n" + "="*70)
    print("📋 REGISTERING WORKFLOWS TO GLOBAL REGISTRY")
    print("="*70)

    for workflow_id in runner.list_workflows():
        success = runner.register_workflow_to_registry(workflow_id)
        status = "✅" if success else "❌"
        print(f"{status} Registered '{workflow_id}' to registry")


def demo_schedule_creation():
    """Demonstrate creating schedules from workflow definitions."""
    print("\n" + "="*70)
    print("⏰ CREATING SCHEDULES FROM WORKFLOW DEFINITIONS")
    print("="*70)

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
            print(f"✅ Scheduled '{workflow_id}':")
            print(f"  Frequency: {schedule.frequency}")
            if schedule.time_of_day:
                print(f"  Time: {schedule.time_of_day}")
            print(f"  Next Run: {schedule.next_run}")
            print()


def demo_workflow_execution():
    """Demonstrate executing a workflow end-to-end."""
    print("\n" + "="*70)
    print("🚀 EXECUTING WORKFLOW END-TO-END")
    print("="*70)

    # This would normally run the full extraction and processing
    # For demo purposes, we'll show the structure
    workflow_id = "electronics_monitoring"
    print(f"\nDemo: Executing workflow '{workflow_id}'...")
    print("Steps to execute:")

    workflow_def = runner.get_workflow(workflow_id)
    for i, step in enumerate(workflow_def.get("steps", []), 1):
        print(f"  {i}. {step}")

    print(f"\n💡 To execute, use: runner.execute_workflow('{workflow_id}')")


def demo_workflow_structure():
    """Show the structure of a workflow definition."""
    print("\n" + "="*70)
    print("📐 WORKFLOW DEFINITION STRUCTURE")
    print("="*70)

    workflow_def = runner.get_workflow("electronics_monitoring")

    print("\n📋 Workflow Definition:")
    print(json.dumps(workflow_def, indent=2))


def main():
    """Run all demonstrations."""
    print("\n" + "🎯 "*25)
    print("DECLARATIVE WORKFLOW ORCHESTRATION DEMONSTRATION")
    print("🎯 "*25)

    demo_load_workflows()
    demo_workflow_config_conversion()
    demo_workflow_registration()
    demo_schedule_creation()
    demo_workflow_execution()
    demo_workflow_structure()

    print("\n" + "="*70)
    print("✅ WORKFLOW RUNNER DEMONSTRATION COMPLETE")
    print("="*70)

    print("\n📚 Key Takeaways:")
    print("  • Workflows are now declarative JSON definitions")
    print("  • WorkflowRunner loads and orchestrates execution")
    print("  • Workflows can be scheduled independently")
    print("  • Execution steps are modular and extensible")
    print("  • No code changes needed to add/modify workflows")
    print("\n")


if __name__ == "__main__":
    main()
