# ADR-0003: Das konkrete User-Model bleibt im Tool

Status: angenommen (2026-07-18)

## Kontext

Beide Bestandstools haben `accounts.User` mit tool-spezifischen Feldern, deren
Migrationshistorien bereits verwoben sind (ausleihbar: `claims`, Strikes,
`anonymized_at`/Retention; abstimmbar: `easy_mode`). Django erlaubt das
Austauschen des User-Models nach der ersten Migration praktisch nicht, und
eine geteilte konkrete Model-Klasse würde jede tool-spezifische Erweiterung
zur Basis-Änderung machen.

## Entscheidung

`basicbar-auth` liefert:

- `AbstractBasicUser` (abstrakt): `subject`, `claims`, OIDC-relevante Felder
  und Verhalten;
- die OIDC-Machinerie: Backend (`OIDCBackend`), `SilentLoginView`,
  Discovery, Back-Channel-Logout, `claims_in_admin_group()`;
- optionale, konfigurierbare Bausteine nach dem Vorbild von ausleihbars
  Usermanagement: Account-Obergrenze (`MAX_USERS`), Retention/Anonymisierung
  inaktiver Accounts, `is_oidc_admin`-Schutz. Alles per Settings aktivierbar,
  ohne Zwang zur identischen Ausgestaltung pro Tool.

Jedes Tool definiert `accounts.User(AbstractBasicUser)` mit eigenen Feldern
und eigenen Migrationen (das Template liefert die Startfassung).

Der Subject-Drift-Fallback (Username-Match bei neu vergebenen IdP-Subjects,
bisher nur abstimmbar) wird ein **Opt-in-Setting** (Arbeitstitel
`OIDC_MATCH_BY_USERNAME_FALLBACK`, Default aus). Die Betreiber-Doku erklärt
die Wahl: Der Fallback und die Fristen für Retention/Löschung hängen von der
IdP-Policy zur Wiedervergabe von Usernamen/E-Mail-Adressen ab — Faustregel:
Anonymisierungsfrist deutlich kürzer als die Mindest-Vakanzzeit des IdP;
werden Kennungen nie neu vergeben (Stand 2026 an der UOS), ist der Fallback
unkritisch. Die Software bleibt standort-neutral; die Policy ist
Konfiguration.

## Konsequenzen

- Bestehende Tools können `basicbar-auth` adoptieren, ohne ihr User-Model
  oder ihre Migrationen anzufassen (Backend/Views zuerst, Abstract-Basis beim
  nächsten natürlichen Anlass).
- Tool-spezifische Felder (Strikes, `easy_mode`, …) bleiben da, wo ihre
  Fachlogik lebt.
