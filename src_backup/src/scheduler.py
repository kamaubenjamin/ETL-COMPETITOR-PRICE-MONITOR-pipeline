"""
Workflow scheduler for automated execution on a timer.
Supports hourly, daily, and custom scheduling.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ScheduledWorkflow:
    """Configuration for a scheduled workflow."""
    workflow_id: str
    frequency: str  # "hourly", "daily", "weekly", "manual"
    time_of_day: Optional[str] = None  # HH:MM format for daily/weekly
    day_of_week: Optional[str] = None  # "monday", "tuesday", etc. for weekly
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "ScheduledWorkflow":
        """Create from dictionary."""
        return ScheduledWorkflow(**data)


class WorkflowScheduler:
    """Manages workflow scheduling and execution history."""

    def __init__(self, schedule_file: str = "src/schedules.json"):
        self.schedule_file = schedule_file
        self.schedules: Dict[str, ScheduledWorkflow] = {}
        self.load_schedules()

    def create_schedule(
        self,
        workflow_id: str,
        frequency: str,
        time_of_day: Optional[str] = None,
        day_of_week: Optional[str] = None,
    ) -> ScheduledWorkflow:
        """Create a new workflow schedule."""
        schedule = ScheduledWorkflow(
            workflow_id=workflow_id,
            frequency=frequency,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            enabled=True,
        )
        schedule.next_run = self.get_next_run(schedule).isoformat() if self.get_next_run(schedule) else None
        self.schedules[workflow_id] = schedule
        self.save_schedules()
        return schedule

    def update_schedule(self, workflow_id: str, **kwargs) -> Optional[ScheduledWorkflow]:
        """Update an existing schedule."""
        if workflow_id not in self.schedules:
            return None
        
        schedule = self.schedules[workflow_id]
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        schedule.next_run = self.get_next_run(schedule).isoformat() if self.get_next_run(schedule) else None
        self.save_schedules()
        return schedule

    def get_schedule(self, workflow_id: str) -> Optional[ScheduledWorkflow]:
        """Retrieve a schedule by workflow ID."""
        return self.schedules.get(workflow_id)

    def list_schedules(self) -> List[ScheduledWorkflow]:
        """List all schedules."""
        return list(self.schedules.values())

    def list_enabled(self) -> List[ScheduledWorkflow]:
        """List all enabled schedules."""
        return [s for s in self.schedules.values() if s.enabled]

    def record_run(self, workflow_id: str) -> bool:
        """Record a workflow run."""
        if workflow_id not in self.schedules:
            return False
        
        schedule = self.schedules[workflow_id]
        schedule.last_run = datetime.now().isoformat()
        schedule.run_count += 1
        next_run = self.get_next_run(schedule)
        schedule.next_run = next_run.isoformat() if next_run else None
        self.save_schedules()
        return True

    def get_next_run(self, schedule: ScheduledWorkflow) -> Optional[datetime]:
        """Calculate the next scheduled run time."""
        if schedule.frequency == "manual" or not schedule.enabled:
            return None

        now = datetime.now()
        time_of_day = None
        if schedule.time_of_day:
            target_hour, target_min = map(int, schedule.time_of_day.split(":"))
            time_of_day = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)

        if schedule.last_run is None:
            if schedule.frequency == "hourly":
                return now
            if schedule.frequency == "daily":
                if time_of_day:
                    return time_of_day if time_of_day > now else time_of_day + timedelta(days=1)
                return now
            if schedule.frequency == "weekly":
                if schedule.day_of_week:
                    weekdays = {
                        "monday": 0,
                        "tuesday": 1,
                        "wednesday": 2,
                        "thursday": 3,
                        "friday": 4,
                        "saturday": 5,
                        "sunday": 6,
                    }
                    target_weekday = weekdays.get(schedule.day_of_week.lower(), now.weekday())
                    days_ahead = (target_weekday - now.weekday()) % 7
                    next_run = now + timedelta(days=days_ahead)
                    if time_of_day:
                        next_run = next_run.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                        if next_run <= now:
                            next_run += timedelta(days=7)
                    return next_run
                return now
            return None

        last_run = datetime.fromisoformat(schedule.last_run)
        if schedule.frequency == "hourly":
            return last_run + timedelta(hours=1)

        if schedule.frequency == "daily":
            if time_of_day:
                next_run = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            return last_run + timedelta(days=1)

        if schedule.frequency == "weekly":
            weekdays = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            if schedule.day_of_week and schedule.day_of_week.lower() in weekdays:
                target_weekday = weekdays[schedule.day_of_week.lower()]
                next_run = now + timedelta(days=(target_weekday - now.weekday()) % 7)
                if time_of_day:
                    next_run = next_run.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=7)
                return next_run
            return last_run + timedelta(days=7)

        return None

    def is_due(self, schedule: ScheduledWorkflow) -> bool:
        """Check if a workflow is due to run."""
        if not schedule.enabled:
            return False
        
        now = datetime.now()
        
        if schedule.frequency == "manual":
            return False
        
        if schedule.last_run is None:
            return True  # Never run before
        
        last_run = datetime.fromisoformat(schedule.last_run)
        
        if schedule.frequency == "hourly":
            return (now - last_run).total_seconds() >= 3600
        
        elif schedule.frequency == "daily":
            # Check if enough time has passed and if time_of_day matches
            if (now - last_run).total_seconds() < 86400:
                return False
            
            if schedule.time_of_day:
                target_hour, target_min = map(int, schedule.time_of_day.split(":"))
                return now.hour == target_hour and now.minute == target_min
            
            return True
        
        elif schedule.frequency == "weekly":
            # Check if enough time has passed and if day/time match
            if (now - last_run).total_seconds() < 604800:  # 7 days
                return False
            
            days = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            
            if schedule.day_of_week and schedule.day_of_week.lower() in days:
                target_day = days[schedule.day_of_week.lower()]
                if now.weekday() != target_day:
                    return False
            
            if schedule.time_of_day:
                target_hour, target_min = map(int, schedule.time_of_day.split(":"))
                return now.hour == target_hour and now.minute == target_min
            
            return True
        
        return False

    def save_schedules(self):
        """Save schedules to file."""
        os.makedirs(os.path.dirname(self.schedule_file) or ".", exist_ok=True)
        with open(self.schedule_file, "w") as f:
            data = {
                wid: schedule.to_dict()
                for wid, schedule in self.schedules.items()
            }
            json.dump(data, f, indent=2)

    def load_schedules(self):
        """Load schedules from file."""
        if not os.path.exists(self.schedule_file):
            return
        
        try:
            with open(self.schedule_file, "r") as f:
                data = json.load(f)
            self.schedules = {
                wid: ScheduledWorkflow.from_dict(sdata)
                for wid, sdata in data.items()
            }
        except Exception:
            self.schedules = {}

    def delete_schedule(self, workflow_id: str) -> bool:
        """Delete a schedule."""
        if workflow_id not in self.schedules:
            return False
        
        del self.schedules[workflow_id]
        self.save_schedules()
        return True


# Global scheduler instance
scheduler = WorkflowScheduler()
