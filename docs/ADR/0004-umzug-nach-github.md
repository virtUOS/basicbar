# ADR-0004: Umzug von GitLab nach GitHub

Status: angenommen (2026-08-04)

## Kontext

basicbar lag bislang auf der internen Uni-Osnabrück-GitLab-Instanz
(`gitlab.uni-osnabrueck.de`), öffentlich sichtbar, damit Tools die
Django-Pakete als Archiv-Tarball ohne Credentials installieren können
(ADR-0002). Das reicht für Tools, die selbst auf derselben Instanz liegen
oder zumindest aus dem Uni-Netz/per VPN bauen.

abstimmBAR ist als erstes „-bar“-Tool zusätzlich öffentlich auf GitHub
gespiegelt (`github.com/virtUOS/abstimmbar`) und baut sein Release-Image über
GitHub Actions auf GitHub-gehosteten Runnern. Diese Runner haben keinen
Netzwerkzugriff auf `gitlab.uni-osnabrueck.de` — das ist keine
Auth-/Sichtbarkeitsfrage (das Projekt war bereits public), sondern schlicht
Netzwerk-Nichterreichbarkeit von außerhalb des Uni-Netzes
(„Network is unreachable“, kein 401/404). Der Image-Build schlug entsprechend
beim `pip install` der basicbar-Pakete fehl.

Zusätzlich: Ziel ist, Beiträge auch von anderen Hochschulen zu ermöglichen —
das setzt einen für Externe leicht auffindbaren, ohne Uni-Zugang nutzbaren
Ort voraus.

## Entscheidung

**basicbar zieht vollständig nach `github.com/virtUOS/basicbar` um** (nicht
nur eine Paket-Spiegelung). Historie und alle Paket-Tags wurden per
`git push --mirror` übernommen. GitHub ist ab sofort der kanonische Ort für
Quelle, Issues/PRs und Releases.

Damit einher:

- **CI**: `.gitlab-ci.yml` durch `.github/workflows/ci.yml` (SPDX-Check,
  Paket-Tests, UI-Build) und `.github/workflows/publish.yml`
  (Release-Publish bei `ui/v*`-Tags) ersetzt.
- **Django-Pakete**: weiterhin Archiv-Tarball vom Tag, jetzt von
  `github.com/virtUOS/basicbar/archive/refs/tags/<tag>.tar.gz` statt vom
  GitLab-Pendant — gleiches Prinzip, andere URL.
- **`@basicbar/ui`**: statt GitLab Generic Package Registry jetzt ein
  GitHub-Release-Asset (`npm pack` in der CI, Upload als Release-Anhang beim
  `ui/v*`-Tag). Bewusst **kein** öffentlicher npm-Registry-Publish — das hätte
  ein `@basicbar`-npm-Scope, ein Account und ein Token samt Rotation
  gebraucht; ein Release-Asset ist wie der Django-Tarball eine reine
  öffentliche URL ohne Registry-Betrieb oder Credentials.
- **Copier-Template**: Quelle für `copier copy`/`copier update` ist jetzt
  `https://github.com/virtUOS/basicbar.git`.
- **Workflow-Sprache**: „Branch + MR“ → „Branch + PR“ (siehe CLAUDE.md).

Für andere zukünftige öffentliche „-bar“-Tools ist das derselbe,
wiederverwendbare Distributionsweg — kein Sonderfall nur für abstimmBAR.

## Konsequenzen

- Die alte GitLab-Instanz war der einzige kanonische Ort; ob das
  GitLab-Projekt archiviert oder gelöscht wird, ist eine
  Hosting-/Policy-Entscheidung der Uni und nicht Teil dieser ADR.
- Interne „-bar“-Tools, die noch auf der Uni-GitLab liegen (z. B.
  ausleihBAR, erkennBAR) und die alten GitLab-Archiv-URLs referenzieren,
  brauchen eigene Folge-MRs, um auf die neuen GitHub-URLs umzustellen. Ihr CI
  läuft weiter auf der Uni-GitLab-Instanz; das ist unproblematisch, solange
  ausgehende Verbindungen zu github.com von dort erlaubt sind (in aller Regel
  der Fall, anders als der umgekehrte Weg).
- Kein Registry-Betrieb für `@basicbar/ui` nötig, dafür kein `npm view`/keine
  Semver-Ranges für Konsumenten — Tarball-URL muss bei jedem Update exakt
  gehoben werden (wie schon zuvor bei der GitLab Generic Package Registry).
