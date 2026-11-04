# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Token-guarded Prometheus endpoint (text exposition format 0.0.4).

Dependency-free: the package renders gauges itself instead of pulling in
``prometheus_client`` — the tools only expose a handful of snapshot values
computed from the database on each scrape, no process-state counters.

A tool subclasses :class:`MetricsView`, implements :meth:`MetricsView.collect`
and mounts it itself (outside ``/api/``). The endpoint is off (404) until
``METRICS_TOKEN`` is set; scrapers then send ``Authorization: Bearer <token>``.
"""

import hmac
import math
import re
from collections.abc import Iterable

from django.http import HttpResponse
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.views import APIView

from . import conf

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Used with ``fullmatch`` (``$`` alone would accept a trailing newline).
_METRIC_NAME = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*")
# Label names may not contain ":" in Prometheus' data model.
_LABEL_NAME = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

Number = float | int


def _format_value(value: Number) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "+Inf" if value > 0 else "-Inf"
    if value.is_integer():
        return str(int(value))
    return repr(value)


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _escape_help(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n")


class Gauges:
    """Collects gauge samples and renders them in Prometheus text format."""

    def __init__(self) -> None:
        self._families: dict[str, list[str]] = {}

    def gauge(
        self,
        name: str,
        help_text: str,
        value: Number | None = None,
        labels: Iterable[tuple[dict[str, str], Number]] | None = None,
    ) -> None:
        """Add one gauge family.

        ``value`` adds an unlabelled sample, ``labels`` an iterable of
        ``(label_dict, value)`` pairs. Invalid metric/label names, a
        repeated family name and a repeated label set within the family
        raise ``ValueError`` (programming errors).
        """
        if not _METRIC_NAME.fullmatch(name):
            raise ValueError(f"Invalid metric name: {name!r}")
        if name in self._families:
            raise ValueError(f"Duplicate metric family: {name!r}")
        lines = [
            f"# HELP {name} {_escape_help(help_text)}",
            f"# TYPE {name} gauge",
        ]
        if value is not None:
            lines.append(f"{name} {_format_value(value)}")
        seen: set[frozenset[tuple[str, str]]] = set()
        for label_dict, sample in labels or ():
            label_set = frozenset((k, str(v)) for k, v in label_dict.items())
            if label_set in seen:
                raise ValueError(f"Duplicate label set in {name!r}: {label_dict!r}")
            seen.add(label_set)
            parts = []
            for key, label_value in label_dict.items():
                if not _LABEL_NAME.fullmatch(key):
                    raise ValueError(f"Invalid label name: {key!r}")
                parts.append(f'{key}="{_escape_label_value(str(label_value))}"')
            lines.append(f"{name}{{{','.join(parts)}}} {_format_value(sample)}")
        self._families[name] = lines

    def render(self) -> str:
        """All families in insertion order, with a trailing newline."""
        return "".join("\n".join(lines) + "\n" for lines in self._families.values())


class _IgnoreAccept(BaseContentNegotiation):
    """Never 406: scrapers send ``Accept: text/plain;version=0.0.4`` (or
    OpenMetrics), which DRF's JSON/browsable renderers would reject before
    the token check. The view returns plain ``HttpResponse`` objects anyway;
    only DRF's own errors (405) use the first renderer."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class MetricsView(APIView):
    """``GET`` the tool's gauges; subclasses implement :meth:`collect`.

    404 while ``METRICS_TOKEN`` is empty, 401 (``WWW-Authenticate: Bearer``)
    unless the request carries exactly ``Authorization: Bearer <token>``.
    """

    authentication_classes = ()
    permission_classes = ()
    # A consumer's DEFAULT_THROTTLE_CLASSES must never rate-limit scrapes.
    throttle_classes = ()
    content_negotiation_class = _IgnoreAccept
    # No OPTIONS: DRF would answer it with view metadata, bypassing the token.
    http_method_names = ("get", "head")

    def collect(self, gauges: Gauges) -> None:
        """Add the tool's gauges to ``gauges``."""
        raise NotImplementedError

    def get(self, request) -> HttpResponse:
        token = conf.get("METRICS_TOKEN")
        if not token:
            response = HttpResponse(status=404)
        elif not hmac.compare_digest(
            request.META.get("HTTP_AUTHORIZATION", "").encode(),
            f"Bearer {token}".encode(),
        ):
            response = HttpResponse(status=401)
            response["WWW-Authenticate"] = "Bearer"
        else:
            gauges = Gauges()
            self.collect(gauges)
            response = HttpResponse(gauges.render(), content_type=CONTENT_TYPE)
        response["Cache-Control"] = "no-store"
        return response
