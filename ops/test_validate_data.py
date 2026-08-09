#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime as dt
import unittest

import validate_data


class ValidateDataDatesTest(unittest.TestCase):
    TODAY = dt.date(2026, 8, 9)

    def problems_for(self, key, value):
        problems = []
        validate_data.walk({key: value}, "fixture", problems, self.TODAY)
        return problems

    def test_future_deadline_is_allowed(self):
        self.assertEqual(self.problems_for("deadline", "2026-08-24"), [])

    def test_future_scheduled_at_is_allowed(self):
        self.assertEqual(self.problems_for("scheduled_at", "2026-09-01T10:00:00"), [])

    def test_future_snapshot_is_rejected(self):
        problems = self.problems_for("snapshot", "2026-08-24")
        self.assertTrue(any("в будущем" in item for item in problems))

    def test_invalid_calendar_date_is_rejected(self):
        problems = self.problems_for("deadline", "2026-02-30")
        self.assertTrue(any("не существует" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
