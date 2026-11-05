# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Test-only view subclasses, mounted in ``tests/urls.py``."""

from basicbar_integrations.metrics import MetricsView


class DemoMetricsView(MetricsView):
    def collect(self, gauges):
        gauges.gauge("demo_total", "Demo", 3)
        gauges.gauge("demo", "Demo by kind", labels=[({"kind": "a"}, 1)])
