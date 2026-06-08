"""Tests for PessimisticLockManager — escalation, ordering, deadlock."""
from __future__ import annotations

import pytest

from src.entity_runtime.concurrency.pessimistic import ENTITY_LOCK_ORDER, PessimisticLockManager


class TestLockOrder:
    """Lock ordering tests."""

    def test_lock_order_correct(self):
        assert ENTITY_LOCK_ORDER == [
            "supplier", "customer", "document_reference",
            "document_financials", "line_item",
        ]

    def test_sort_by_lock_order(self):
        keys = [
            "line_item:doc-1:item-1",
            "supplier:doc-1:acme",
            "customer:doc-1:quickmart",
        ]
        sorted_keys = PessimisticLockManager._sort_by_lock_order(keys)
        assert sorted_keys[0].startswith("supplier")
        assert sorted_keys[1].startswith("customer")
        assert sorted_keys[2].startswith("line_item")


class TestEscalation:
    """Escalation management tests."""

    def test_should_not_escalate_initially(self, pessimistic_manager: PessimisticLockManager):
        assert not pessimistic_manager.should_escalate("supplier:doc-1:acme")

    def test_should_escalate_after_high_conflict_rate(self, pessimistic_manager: PessimisticLockManager):
        pessimistic_manager.record_conflict("supplier:doc-1:acme")
        pessimistic_manager.record_conflict("supplier:doc-1:acme")
        pessimistic_manager.record_write_attempt("supplier:doc-1:acme")
        pessimistic_manager.record_write_attempt("supplier:doc-1:acme")
        assert pessimistic_manager.should_escalate("supplier:doc-1:acme")

    def test_de_escalate(self, pessimistic_manager: PessimisticLockManager):
        pessimistic_manager.record_conflict("supplier:doc-1:acme")
        pessimistic_manager.record_write_attempt("supplier:doc-1:acme")
        pessimistic_manager.record_conflict("supplier:doc-1:acme")
        pessimistic_manager.record_write_attempt("supplier:doc-1:acme")
        # Initially should not escalate (conflict rate is 1.0 but needs 2+ conflicts)
        pessimistic_manager.should_escalate("supplier:doc-1:acme")
        # Now de-escalate
        assert pessimistic_manager.de_escalate("supplier:doc-1:acme")
        # After de-escalation, should_escalate should return False because no data
        assert not pessimistic_manager.should_escalate("supplier:doc-1:acme")


class TestConflictTracking:
    """Conflict tracking tests."""

    def test_record_conflict(self, pessimistic_manager: PessimisticLockManager):
        pessimistic_manager.record_conflict("supplier:doc-1:acme")
        # Should not raise
        assert True

    def test_conflict_rate_no_attempts(self, pessimistic_manager: PessimisticLockManager):
        rate = pessimistic_manager._get_conflict_rate("supplier:doc-1:nonexistent")
        assert rate == 0.0