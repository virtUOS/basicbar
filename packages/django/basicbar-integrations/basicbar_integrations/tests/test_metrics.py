# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)
from django.test import SimpleTestCase, TestCase, override_settings

from basicbar_integrations.metrics import Gauges, MetricsView

# The view under test is ``tests.views.DemoMetricsView``, mounted at /metrics.


class GaugesRenderTests(SimpleTestCase):
    def test_render_unlabelled(self):
        g = Gauges()
        g.gauge("demo_total", "Demo", 3)
        self.assertEqual(
            g.render(),
            "# HELP demo_total Demo\n# TYPE demo_total gauge\ndemo_total 3\n",
        )

    def test_render_labelled(self):
        g = Gauges()
        g.gauge("demo", "Demo", labels=[({"kind": "a"}, 1), ({"kind": "b"}, 0)])
        out = g.render()
        self.assertIn('demo{kind="a"} 1\n', out)
        self.assertIn('demo{kind="b"} 0\n', out)
        self.assertTrue(out.startswith("# HELP demo Demo\n# TYPE demo gauge\n"))

    def test_label_escaping(self):
        g = Gauges()
        g.gauge("demo", "Demo", labels=[({"kind": 'a"b\nc'}, 1)])
        self.assertIn('demo{kind="a\\"b\\nc"} 1\n', g.render())

    def test_backslash_escaping(self):
        g = Gauges()
        g.gauge("demo", "Demo", labels=[({"kind": "a\\b"}, 1)])
        self.assertIn('demo{kind="a\\\\b"} 1\n', g.render())

    def test_float_and_int(self):
        g = Gauges()
        g.gauge("a", "A", 2.5)
        g.gauge("b", "B", 2.0)
        out = g.render()
        self.assertIn("\na 2.5\n", out)
        self.assertIn("\nb 2\n", out)

    def test_invalid_name_raises(self):
        g = Gauges()
        with self.assertRaises(ValueError):
            g.gauge("1bad", "Bad", 1)
        with self.assertRaises(ValueError):
            g.gauge("demo", "Demo", labels=[({"kind-x": "a"}, 1)])

    def test_trailing_newline_in_names_raises(self):
        g = Gauges()
        with self.assertRaises(ValueError):
            g.gauge("demo\n", "Demo", 1)
        with self.assertRaises(ValueError):
            g.gauge("demo", "Demo", labels=[({"k\n": "a"}, 1)])

    def test_duplicate_label_set_raises(self):
        g = Gauges()
        with self.assertRaises(ValueError):
            g.gauge(
                "demo",
                "Demo",
                labels=[({"a": "1", "b": "2"}, 1), ({"b": "2", "a": "1"}, 2)],
            )

    def test_distinct_label_sets_ok(self):
        g = Gauges()
        g.gauge("demo", "Demo", labels=[({"a": "1"}, 1), ({"a": "2"}, 2)])
        self.assertIn('demo{a="2"} 2\n', g.render())

    def test_duplicate_family_raises(self):
        g = Gauges()
        g.gauge("demo", "Demo", 1)
        with self.assertRaises(ValueError):
            g.gauge("demo", "Demo", 2)

    def test_families_in_insertion_order(self):
        g = Gauges()
        g.gauge("zeta", "Z", 1)
        g.gauge("alpha", "A", 1)
        out = g.render()
        self.assertLess(out.index("zeta"), out.index("alpha"))

    def test_empty_render(self):
        self.assertEqual(Gauges().render(), "")


class MetricsViewTests(TestCase):
    ACCEPTS = (
        "text/plain",
        "text/plain;version=0.0.4",
        "application/openmetrics-text;version=1.0.0,text/plain;version=0.0.4;q=0.5",
        "application/json",
    )

    def _get(self, auth=None, **headers):
        if auth is not None:
            headers["HTTP_AUTHORIZATION"] = auth
        return self.client.get("/metrics", **headers)

    def test_accept_header_ignored_without_token(self):
        for accept in self.ACCEPTS:
            with self.subTest(accept=accept):
                self.assertEqual(self._get(HTTP_ACCEPT=accept).status_code, 404)

    @override_settings(METRICS_TOKEN="tok")
    def test_accept_header_ignored_with_token(self):
        for accept in self.ACCEPTS:
            with self.subTest(accept=accept):
                response = self._get("Bearer tok", HTTP_ACCEPT=accept)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], self.CONTENT_TYPE)
                self.assertIn("demo_total 3", response.content.decode())
                self.assertEqual(
                    self._get("Bearer x", HTTP_ACCEPT=accept).status_code, 401
                )

    @override_settings(METRICS_TOKEN="tok")
    def test_format_query_param_ignored(self):
        response = self.client.get(
            "/metrics?format=json", HTTP_AUTHORIZATION="Bearer tok"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("demo_total 3", response.content.decode())

    def test_consumer_throttles_do_not_apply(self):
        # DRF binds DEFAULT_THROTTLE_CLASSES at class creation, so a project
        # default would be inherited; the view must opt out explicitly.
        self.assertEqual(MetricsView.throttle_classes, ())
        self.assertEqual(MetricsView().get_throttles(), [])

    CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

    def test_404_without_token(self):
        self.assertEqual(self._get("Bearer ").status_code, 404)
        self.assertEqual(self._get().status_code, 404)

    @override_settings(METRICS_TOKEN="tok")
    def test_401_missing_header(self):
        response = self._get()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

    @override_settings(METRICS_TOKEN="tok")
    def test_401_wrong_token(self):
        response = self._get("Bearer nope")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

    @override_settings(METRICS_TOKEN="tok")
    def test_header_variants_are_401(self):
        for header in ("Bearer tok ", "bearer tok", "tok", "Basic tok"):
            with self.subTest(header=header):
                self.assertEqual(self._get(header).status_code, 401)

    @override_settings(METRICS_TOKEN="tok")
    def test_200_with_token(self):
        response = self._get("Bearer tok")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8"
        )
        self.assertEqual(response["Cache-Control"], "no-store")
        body = response.content.decode()
        self.assertIn("# TYPE demo_total gauge", body)
        self.assertIn('demo{kind="a"} 1', body)

    @override_settings(METRICS_TOKEN="tok")
    def test_post_is_405(self):
        response = self.client.post("/metrics", HTTP_AUTHORIZATION="Bearer tok")
        self.assertEqual(response.status_code, 405)

    @override_settings(METRICS_TOKEN="tok")
    def test_options_is_405(self):
        self.assertEqual(self.client.options("/metrics").status_code, 405)

    @override_settings(METRICS_TOKEN="tok")
    def test_head_requires_token(self):
        self.assertEqual(self.client.head("/metrics").status_code, 401)
        ok = self.client.head("/metrics", HTTP_AUTHORIZATION="Bearer tok")
        self.assertEqual(ok.status_code, 200)

    @override_settings(METRICS_TOKEN="tok")
    def test_401_has_no_store(self):
        self.assertEqual(self._get()["Cache-Control"], "no-store")


class AbstractCollectTests(SimpleTestCase):
    def test_collect_is_abstract(self):
        with self.assertRaises(NotImplementedError):
            MetricsView().collect(Gauges())
