"""
Test script demonstrating scheduler and reporter integration.
"""
import sys
import os
from datetime import datetime, timedelta

# Add workspace to path
sys.path.insert(0, os.path.dirname(__file__))

from src.scheduler import scheduler
from src.reporter import reporter
from src.workflows import registry


def test_scheduler_creation():
    """Test creating and managing schedules."""
    print("=" * 60)
    print("Testing Scheduler Creation")
    print("=" * 60)
    
    # Create a schedule
    schedule = scheduler.create_schedule(
        workflow_id="electronics_monitoring",
        frequency="daily",
        time_of_day="14:30",
    )
    
    print(f"✅ Created schedule: {schedule.workflow_id}")
    print(f"   Frequency: {schedule.frequency}")
    print(f"   Time: {schedule.time_of_day}")
    print(f"   Enabled: {schedule.enabled}")
    print()
    
    # List schedules
    schedules = scheduler.list_schedules()
    print(f"📋 Total schedules: {len(schedules)}")
    for s in schedules:
        print(f"   - {s.workflow_id} ({s.frequency})")
    print()


def test_scheduler_execution_check():
    """Test checking if workflows are due."""
    print("=" * 60)
    print("Testing Scheduler Execution Checks")
    print("=" * 60)
    
    # Create different types of schedules
    schedules_to_test = [
        ("hourly_workflow", "hourly", None, None),
        ("daily_workflow", "daily", "14:30", None),
        ("weekly_workflow", "weekly", "10:00", "monday"),
    ]
    
    for wid, freq, time, day in schedules_to_test:
        schedule = scheduler.create_schedule(
            workflow_id=wid,
            frequency=freq,
            time_of_day=time,
            day_of_week=day,
        )
        
        is_due = scheduler.is_due(schedule)
        print(f"📍 {wid}")
        print(f"   Frequency: {freq}")
        print(f"   Is due: {is_due}")
        print()


def test_schedule_recording():
    """Test recording workflow runs."""
    print("=" * 60)
    print("Testing Schedule Recording")
    print("=" * 60)
    
    wid = "test_workflow"
    schedule = scheduler.create_schedule(
        workflow_id=wid,
        frequency="daily",
        time_of_day="12:00",
    )
    
    print(f"Initial run count: {schedule.run_count}")
    print(f"Last run: {schedule.last_run}")
    print()
    
    # Record a run
    scheduler.record_run(wid)
    schedule = scheduler.get_schedule(wid)
    
    print(f"After recording:")
    print(f"   Run count: {schedule.run_count}")
    print(f"   Last run: {schedule.last_run}")
    print()


def test_reporter_summary():
    """Test reporter summary generation."""
    print("=" * 60)
    print("Testing Reporter Summary")
    print("=" * 60)
    
    import pandas as pd
    
    # Create sample data
    comparison_df = pd.DataFrame({
        'product_name': ['TV A', 'TV B', 'TV C'],
        'source_1': [100, 200, 300],
        'source_2': [95, 210, 280],
        'cheapest': ['source_2', 'source_1', 'source_2'],
    })
    
    alerts = [
        "Price drop detected: TV A KES 5 cheaper at Source 2",
        "Price increase: TV B KES 10 higher at Source 2",
        "Undercut alert: TV C at Source 2 undercuts by KES 20",
    ]
    
    summary = reporter.generate_summary(comparison_df, alerts, "Test Workflow")
    
    print("📊 Workflow Summary:")
    print(f"   Workflow: {summary['workflow']}")
    print(f"   Timestamp: {summary['timestamp']}")
    print(f"   Products compared: {summary['products_compared']}")
    print(f"   Total alerts: {summary['total_alerts']}")
    print(f"   Price differences found: {summary['price_differences']}")
    print()


def cleanup_test_schedules():
    """Clean up test schedules."""
    print("=" * 60)
    print("Cleaning up test schedules")
    print("=" * 60)
    
    for schedule in scheduler.list_schedules():
        if schedule.workflow_id in [
            "test_workflow",
            "hourly_workflow",
            "daily_workflow",
            "weekly_workflow",
        ]:
            scheduler.delete_schedule(schedule.workflow_id)
            print(f"✅ Deleted: {schedule.workflow_id}")
    
    print()


if __name__ == "__main__":
    print("\n🚀 Scheduler & Reporter Integration Test\n")
    
    try:
        test_scheduler_creation()
        test_scheduler_execution_check()
        test_schedule_recording()
        test_reporter_summary()
        cleanup_test_schedules()
        
        print("=" * 60)
        print("✅ All integration tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
