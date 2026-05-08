"""
Demonstration of scheduler + reporter integration with workflow execution.
Shows how scheduled workflows would run and generate reports.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from src.scheduler import scheduler
from src.reporter import reporter
from src.workflows import registry
from src.storage.history_store import detect_price_changes
from src.alerts.alert_engine import generate_alerts
import pandas as pd


def create_demo_comparison_data():
    """Create realistic comparison data for demo."""
    return pd.DataFrame({
        'product_name': [
            'Samsung 55" QLED TV',
            'LG 65" OLED TV',
            'Sony Bravia 50" 4K',
            'TCL 32" Smart TV',
        ],
        'source_1': [35000, 45000, 32000, 12000],
        'source_2': [34500, 44800, 31500, 11900],
        'cheapest': ['source_2', 'source_2', 'source_2', 'source_2'],
    })


def create_demo_price_changes():
    """Create sample price change data."""
    return pd.DataFrame({
        'product_name': [
            'Samsung 55" QLED TV',
            'Sony Bravia 50" 4K',
        ],
        'old_price': [35200, 32100],
        'new_price': [35000, 31500],
        'source': ['Jumia', 'Kilimall'],
        'price_change': [-200, -600],
        'change_percentage': [-0.57, -1.87],
        'timestamp': [datetime.now().isoformat(), datetime.now().isoformat()],
    })


def demonstrate_scheduled_execution():
    """Show how a scheduled workflow would execute."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION: Scheduled Workflow Execution")
    print("=" * 70)
    
    # Get the default workflow
    workflow = registry.get("electronics_monitoring")
    if not workflow:
        print("ERROR: electronics_monitoring workflow not found")
        return False
    
    print(f"\nWorkflow: {workflow.name}")
    print(f"Sources: {len(workflow.sources)}")
    for source in workflow.sources:
        print(f"  - {source.name} ({source.source_type})")
    
    # Step 1: Create schedule
    print("\n" + "-" * 70)
    print("STEP 1: Create Schedule")
    print("-" * 70)
    
    schedule = scheduler.create_schedule(
        workflow_id="electronics_monitoring",
        frequency="daily",
        time_of_day="14:30",
    )
    
    print(f"✓ Schedule created for daily execution at {schedule.time_of_day}")
    print(f"  Workflow: {schedule.workflow_id}")
    print(f"  Frequency: {schedule.frequency}")
    print(f"  Enabled: {schedule.enabled}")
    
    # Step 2: Check if due
    print("\n" + "-" * 70)
    print("STEP 2: Check If Workflow Is Due")
    print("-" * 70)
    
    is_due = scheduler.is_due(schedule)
    print(f"Is due now: {is_due}")
    print("(Note: First run is always due, then checks frequency/time)")
    
    # Step 3: Simulate workflow execution
    print("\n" + "-" * 70)
    print("STEP 3: Simulate Workflow Execution")
    print("-" * 70)
    
    print("\nRunning: multi_source_pipeline(workflow, config)")
    print("  └─ Extracting data from sources...")
    print("  └─ Transforming products...")
    print("  └─ Building comparison table...")
    
    # Create demo data
    comparison_df = create_demo_comparison_data()
    price_changes_df = create_demo_price_changes()
    
    print(f"\n✓ Extraction complete: {len(comparison_df)} products")
    print("\nComparison Data:")
    print(comparison_df.to_string(index=False))
    
    # Step 4: Generate alerts
    print("\n" + "-" * 70)
    print("STEP 4: Generate Alerts")
    print("-" * 70)
    
    # Create alert rules from workflow
    print("\nAlert Rules:")
    for rule in workflow.alert_rules:
        print(f"  - {rule.get('type', 'unknown').upper()}: >= {rule.get('threshold', 0)}%")
    
    alerts = generate_alerts(price_changes_df, workflow.alert_rules)
    print(f"\nGenerated Alerts ({len(alerts)}):")
    for alert in alerts:
        print(f"  • {alert}")
    
    # Step 5: Export results
    print("\n" + "-" * 70)
    print("STEP 5: Export Results")
    print("-" * 70)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV exports
    csv_comparison = reporter.export_comparison_csv(comparison_df, workflow.name, timestamp)
    csv_alerts = reporter.export_alerts_csv(alerts, workflow.name, timestamp)
    
    print(f"\n✓ CSV Exports:")
    print(f"  - {os.path.basename(csv_comparison)}")
    print(f"  - {os.path.basename(csv_alerts)}")
    
    # PDF exports
    pdf_alerts = reporter.export_alerts_pdf(alerts, workflow.name, timestamp)
    if pdf_alerts:
        print(f"  - {os.path.basename(pdf_alerts)} (PDF)")
    else:
        print(f"  - PDF generation skipped (reportlab not available)")
    
    # Step 6: Record execution
    print("\n" + "-" * 70)
    print("STEP 6: Record Execution")
    print("-" * 70)
    
    scheduler.record_run("electronics_monitoring")
    updated_schedule = scheduler.get_schedule("electronics_monitoring")
    
    print(f"\n✓ Execution recorded:")
    print(f"  - Last run: {updated_schedule.last_run}")
    print(f"  - Run count: {updated_schedule.run_count}")
    
    # Step 7: Generate summary
    print("\n" + "-" * 70)
    print("STEP 7: Execution Summary")
    print("-" * 70)
    
    summary = reporter.generate_summary(comparison_df, alerts, workflow.name)
    
    print(f"\nWorkflow Execution Report:")
    print(f"  Workflow: {summary['workflow']}")
    print(f"  Timestamp: {summary['timestamp']}")
    print(f"  Products Compared: {summary['products_compared']}")
    print(f"  Total Alerts: {summary['total_alerts']}")
    print(f"  Price Differences: {summary['price_differences']}")
    
    # Final state
    print("\n" + "=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)
    
    print(f"\nNext scheduled run: Check daily at {schedule.time_of_day}")
    print(f"Results exported to: reports/ folder")
    
    return True


def demonstrate_schedule_management():
    """Show schedule management capabilities."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION: Schedule Management")
    print("=" * 70)
    
    # List all schedules
    print("\nManaging Multiple Workflows:")
    schedules = scheduler.list_schedules()
    
    for i, sched in enumerate(schedules, 1):
        status = "ENABLED" if sched.enabled else "DISABLED"
        print(f"\n{i}. {sched.workflow_id}")
        print(f"   Frequency: {sched.frequency}")
        print(f"   Status: {status}")
        print(f"   Runs: {sched.run_count}")
        if sched.last_run:
            print(f"   Last run: {sched.last_run}")
    
    print("\n" + "-" * 70)
    print("Scheduler Features:")
    print("-" * 70)
    print("""
    ✓ Create multiple schedules for different workflows
    ✓ Set different frequencies (hourly/daily/weekly/manual)
    ✓ Track execution history (last run, run count)
    ✓ Enable/disable schedules without deleting
    ✓ Automatic time-based checks
    ✓ Persistent storage in JSON
    """)


if __name__ == "__main__":
    print("\n" + "🚀" * 35)
    print("\nScheduler + Reporter Integration Demo")
    print("Complete workflow execution with scheduling and reporting\n")
    
    try:
        # Check if default workflow exists
        if not registry.get("electronics_monitoring"):
            print("Creating default workflow for demo...")
            # Will be auto-loaded from src/workflows/ directory
        
        # Run demonstration
        if demonstrate_scheduled_execution():
            demonstrate_schedule_management()
            
            print("\n" + "=" * 70)
            print("✓ DEMO COMPLETE - All features working correctly!")
            print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
