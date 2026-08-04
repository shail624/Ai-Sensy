from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE = "d20fefce1ec1fbdd97cd6bbdbfba2af9df9b9975"
ADR_PATH = Path("docs/adr/0020-enterprise-omnichannel-channel-manager.md")
CHANGELOG_PATH = Path("CHANGELOG.md")

ADR_BLOCK = """## Owner-approved provider classification clarification — 2026-08-05

This append-only owner decision clarifies how the existing provider certification gate distinguishes
official authorization from an owner-approved internal self-hosted deployment. It does not weaken or
remove any Required criterion in Design Document 33 §6.1, alter the architecture, select a provider,
or authorize implementation.

- **Class A — Official Providers.** Official providers, including Meta Cloud API, continue to require
  every existing Required criterion exactly as written. For the Design Document 33 §6.1 **Legal and
  policy position** row, evidence must include documented official authorization plus reviewed
  licensing and data-processing terms.
- **Class B — Owner-approved Internal Self-hosted Providers.** A Class B provider is not an official
  or officially authorized provider. It may be considered only for a named, versioned, internal,
  self-hosted deployment serving one approved organization. For the Design Document 33 §6.1 **Legal
  and policy position** row, evidence must include explicit repository-owner authorization for that
  restricted deployment, reviewed licensing and data-processing terms, Architecture approval,
  Security approval and explicit operational and policy Risk Acceptance acknowledging the absence of
  official provider authorization.
- **Class B deployment boundary.** Public service, public SaaS, multi-customer hosting, reseller use,
  resale and marketplace distribution are prohibited. Class B is not a replacement for Class A and
  does not permit QR campaigns, broadcasts, bulk automation or automatic cross-provider failover.
- **Class B mandatory controls.** Certification must prove disabled-by-default organization-scoped
  feature flags, existing RBAC and object authorization, tenant and organization isolation, complete
  Audit coverage, operational monitoring and alerting, an effective emergency kill switch, isolated
  runtime and secret handling, and every existing evidence-based Required provider criterion.
  Unsupported, unknown or unevidenced Required criteria remain certification failures.
- **Authorization boundary.** This clarification does not certify WAHA, Evolution API or any other
  provider; does not permit a provider name, SDK or dependency to be committed before its approved
  evidence record; does not unlock M13-06; and does not change roadmap sequencing."""

CHANGELOG_ENTRY = """### 2026-08-05 — ADR-0020 provider classification clarification

**Reason**
- Recorded the repository owner's explicit architecture decision to distinguish official provider
  authorization from an owner-approved internal self-hosted deployment after the existing provider
  gate correctly rejected candidates without official authorization.

**Changed**
- Appended the Class A / Class B distinction to ADR-0020 and defined class-specific evidence for the
  existing Design Document 33 §6.1 Legal and policy position criterion.

**Preserved**
- Every other Required provider criterion, security, RBAC, tenant isolation, Audit, runtime/session
  isolation, monitoring, kill-switch, feature-flag, provider-neutral architecture and repository
  quality requirement remains unchanged.
- No provider is selected or certified, no provider dependency or implementation is added, roadmap
  sequencing is unchanged and M13-06 remains blocked.

**Validated**
- Documentation-only boundary: ADR-0020 and `CHANGELOG.md` only; no source, API, migration, generated
  contract, runtime, provider or milestone-status file changed."""


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def baseline(path: Path) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASE}:{path.as_posix()}"],
        text=True,
    )


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def apply() -> None:
    adr = ADR_PATH.read_text(encoding="utf-8")
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    if adr != baseline(ADR_PATH):
        raise SystemExit("ADR baseline does not match the approved remote HEAD")
    if changelog != baseline(CHANGELOG_PATH):
        raise SystemExit("CHANGELOG baseline does not match the approved remote HEAD")
    if ADR_BLOCK in adr or CHANGELOG_ENTRY in changelog:
        raise SystemExit("provider classification clarification already exists")

    adr_marker = "\n## Consequences\n"
    if adr.count(adr_marker) != 1:
        raise SystemExit("ADR insertion marker is not unique")
    adr = adr.replace(
        adr_marker,
        f"\n{ADR_BLOCK}\n\n## Consequences\n",
        1,
    )

    changelog_marker = "## [Unreleased]\n\n"
    if changelog.count(changelog_marker) != 1:
        raise SystemExit("CHANGELOG insertion marker is not unique")
    changelog = changelog.replace(
        changelog_marker,
        f"{changelog_marker}{CHANGELOG_ENTRY}\n\n",
        1,
    )

    write(ADR_PATH, adr)
    write(CHANGELOG_PATH, changelog)


def validate() -> None:
    adr = ADR_PATH.read_text(encoding="utf-8")
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    base_adr = baseline(ADR_PATH)
    base_changelog = baseline(CHANGELOG_PATH)

    if adr.count(ADR_BLOCK) != 1:
        raise SystemExit("ADR clarification must appear exactly once")
    if changelog.count(CHANGELOG_ENTRY) != 1:
        raise SystemExit("CHANGELOG entry must appear exactly once")
    if adr.replace(f"\n{ADR_BLOCK}\n", "\n", 1) != base_adr:
        raise SystemExit("ADR change is not strictly append-only")
    if changelog.replace(f"{CHANGELOG_ENTRY}\n\n", "", 1) != base_changelog:
        raise SystemExit("CHANGELOG contains changes outside the required entry")

    changed = set(git("diff", "--name-only", BASE).splitlines())
    expected = {
        "CHANGELOG.md",
        "docs/adr/0020-enterprise-omnichannel-channel-manager.md",
    }
    if changed != expected:
        raise SystemExit(f"unexpected changed-file boundary: {sorted(changed ^ expected)}")

    required_phrases = (
        "Class A — Official Providers",
        "Class B — Owner-approved Internal Self-hosted Providers",
        "explicit repository-owner authorization",
        "Architecture approval",
        "Security approval",
        "Risk Acceptance",
        "disabled-by-default organization-scoped",
        "existing RBAC and object authorization",
        "tenant and organization isolation",
        "complete Audit coverage",
        "operational monitoring and alerting",
        "emergency kill switch",
        "isolated runtime and secret handling",
        "Unsupported, unknown or unevidenced Required criteria remain certification failures",
        "does not unlock M13-06",
        "does not change roadmap sequencing",
    )
    missing = [phrase for phrase in required_phrases if phrase not in adr]
    if missing:
        raise SystemExit(f"missing mandatory clarification terms: {missing}")

    prohibited_changes = (
        "ENGINEERING_STANDARDS.md",
        "REPOSITORY_RULES.md",
        "ROADMAP.md",
        "PROJECT_STATE.md",
        "IMPLEMENTATION_TRACKER.md",
        "MODULE_STATUS.md",
        "VALIDATION_RESULTS.md",
        "docs/design/33-MODULE-13-ENTERPRISE-OMNICHANNEL-IMPLEMENTATION-CONTRACT.md",
    )
    for path in prohibited_changes:
        subprocess.check_call(["git", "diff", "--exit-code", BASE, "--", path])

    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    design = Path(
        "docs/design/33-MODULE-13-ENTERPRISE-OMNICHANNEL-IMPLEMENTATION-CONTRACT.md"
    ).read_text(encoding="utf-8")
    if "| M13-06 — QR inbound, history and media |" not in roadmap:
        raise SystemExit("M13-06 roadmap boundary is missing")
    if "Blocked by provider certification" not in roadmap:
        raise SystemExit("M13-06 provider-certification block is missing")
    if "A candidate fails selection if any Required item is unsupported or cannot be evidenced." not in design:
        raise SystemExit("Required provider gate has changed")
    if "A provider name, SDK or dependency must not be committed before this record is approved." not in design:
        raise SystemExit("provider dependency gate has changed")

    subprocess.check_call(["git", "diff", "--check", BASE])
    print("Documentation boundary: PASS")
    print("ADR append-only preservation: PASS")
    print("Required provider criteria unchanged: PASS")
    print("Security/RBAC/tenant/Audit controls preserved: PASS")
    print("Roadmap sequencing unchanged: PASS")
    print("M13-06 remains blocked: PASS")
    print("No provider selected or certified: PASS")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"apply", "validate"}:
        raise SystemExit("usage: finalize_adr_0020_provider_classes.py apply|validate")
    if sys.argv[1] == "apply":
        apply()
    else:
        validate()


if __name__ == "__main__":
    main()
