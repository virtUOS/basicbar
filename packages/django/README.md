# Django-Pakete

Wiederverwendbare Django-Apps, als pip-Pakete direkt aus Git installierbar
(Tags `<paket>/vX.Y.Z`, siehe [ADR-0002](../../docs/ADR/0002-versionierung-und-sync.md)):

| Paket | Inhalt | Phase |
|---|---|---|
| `basicbar-integrations` | LibreTranslate-Client, LiteLLM-Client, Translate-Endpunkt, Capabilities-Endpoint | 2 |
| `basicbar-auth` | OIDC-Backend, Discovery, Silent Login, Back-Channel-Logout, `AbstractBasicUser`, optionale Limits/Retention ([ADR-0003](../../docs/ADR/0003-user-model-bleibt-im-tool.md)) | 4 |
| `basicbar-lti` | LTI-1.3-App (aus abstimmbar), per Env aktivierbar | 5 |

Keine Tool-Fachlogik, keine konkreten User-Models.
