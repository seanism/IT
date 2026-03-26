#!/usr/bin/env python3

"""Find Okta groups that violate naming conventions and are used in app assignments or group rules."""

# Standard library
import csv
import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

try:
    import requests
except ImportError as import_error:
    print(import_error)
    sys.exit(
        "Looks like you need to install the requests module. Open a Terminal and run "
        "python3 -m pip install requests."
    )

########################################################################################
######################### UPDATE VARIABLES BELOW #######################################
########################################################################################

# Your Okta domain, e.g. "yourcompany.okta.com" or "yourcompany.oktapreview.com"
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN")

# Okta API token — generate one in Okta Admin > Security > API > Tokens
OKTA_API_TOKEN = os.getenv("OKTA_API_TOKEN")

# Naming convention as a Python regex. Groups whose names do NOT match are flagged.
#
# The default enforces dot-namespaced groups, e.g.:
#   org.engineering, app.salesforce, team.devops, role.admin, attr.contractor
#
# Other examples:
#   Restrict allowed prefixes further:
#       r"^(org|app|team|role|attr)\.[a-z][a-z0-9._-]+"
#
#   Uppercase prefix with underscore separator:
#       r"^(APP|DEPT|SEC|IT)_\S+"
#
#   Fully custom pattern:
#       r"^YOUR_PATTERN_HERE"
#
NAMING_CONVENTION_REGEX = os.getenv("NAMING_CONVENTION_REGEX", r"^(org|attr|app|team|role)\..+")

########################################################################################


def _headers():
    return {
        "Authorization": f"SSWS {OKTA_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get_all_pages(url, params=None):
    """Fetch every page from an Okta API endpoint, following Link headers."""
    results = []
    while url:
        resp = requests.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        results.extend(resp.json())
        url = resp.links.get("next", {}).get("url")
        params = None  # params are already embedded in the next-page URL
    return results


def get_all_groups():
    url = f"https://{OKTA_DOMAIN}/api/v1/groups"
    return _get_all_pages(url, params={"limit": 200})


def get_group_apps(group_id):
    url = f"https://{OKTA_DOMAIN}/api/v1/groups/{group_id}/apps"
    return _get_all_pages(url, params={"limit": 200})


def get_all_group_rules():
    url = f"https://{OKTA_DOMAIN}/api/v1/groups/rules"
    return _get_all_pages(url, params={"limit": 200})


def find_noncompliant_groups(all_groups, pattern):
    """Return Okta-mastered groups (OKTA_GROUP) whose name does not match the pattern."""
    return [
        g for g in all_groups
        if g.get("type") == "OKTA_GROUP"
        and not pattern.match(g["profile"]["name"])
    ]


def check_app_assignments(noncompliant_groups):
    """Return a dict of group_id -> [app_label, ...] for groups with app assignments."""
    groups_with_apps = {}
    total = len(noncompliant_groups)
    for idx, group in enumerate(noncompliant_groups, 1):
        gid = group["id"]
        gname = group["profile"]["name"]
        # Pad/truncate to a fixed width to avoid leftover characters from longer names
        line = f"  Checking apps [{idx}/{total}]: {gname}"
        print(f"{line:<120}", end="\r")
        apps = get_group_apps(gid)
        if apps:
            groups_with_apps[gid] = [a["label"] for a in apps]
    print()  # newline after progress output
    return groups_with_apps


def check_group_rules(all_rules, nc_ids):
    """
    Return a dict of group_id -> {"target": [...], "condition": [...]} for non-compliant
    groups that appear as rule targets or inside rule condition expressions.
    """
    groups_in_rules = {}
    for rule in all_rules:
        rule_name = rule.get("name", "")
        rule_status = rule.get("status", "UNKNOWN")

        # Groups targeted by this rule (users will be added to these groups)
        target_ids = (
            rule.get("actions", {})
            .get("assignUserToGroups", {})
            .get("groupIds", [])
        )
        for gid in target_ids:
            if gid in nc_ids:
                groups_in_rules.setdefault(gid, {"target": [], "condition": []})
                groups_in_rules[gid]["target"].append(f"{rule_name} [{rule_status}]")

        # Groups referenced inside the rule's condition expression
        # (e.g. isMemberOfGroup("00gXXX") or isMemberOfAnyGroup("00gXXX", ...))
        expression = (
            rule.get("conditions", {})
            .get("expression", {})
            .get("value", "")
        )
        for gid in nc_ids:
            if gid in expression:
                groups_in_rules.setdefault(gid, {"target": [], "condition": []})
                groups_in_rules[gid]["condition"].append(f"{rule_name} [{rule_status}]")

    return groups_in_rules


def get_member_count(group):
    """Return the member count from the group's objectClass stats if available."""
    return group.get("_links", {}).get("users", {}).get("hints", {}).get("allow", None) \
        or group.get("profile", {}).get("memberCount", None)


def write_csv(results, path, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    if not OKTA_DOMAIN or not OKTA_API_TOKEN:
        sys.exit(
            "Missing required environment variables.\n"
            "Set OKTA_DOMAIN and OKTA_API_TOKEN in a .env file or your shell environment."
        )

    try:
        pattern = re.compile(NAMING_CONVENTION_REGEX)
    except re.error as e:
        sys.exit(f"Invalid NAMING_CONVENTION_REGEX: {e}")

    print(f"Okta domain : {OKTA_DOMAIN}")
    print(f"Convention  : {NAMING_CONVENTION_REGEX}\n")

    print("Fetching all Okta groups...")
    all_groups = get_all_groups()
    print(f"  Total groups: {len(all_groups)}")

    okta_groups = [g for g in all_groups if g.get("type") == "OKTA_GROUP"]
    skipped = len(all_groups) - len(okta_groups)
    noncompliant = find_noncompliant_groups(all_groups, pattern)
    nc_ids = {g["id"] for g in noncompliant}
    nc_by_id = {g["id"]: g for g in noncompliant}
    print(f"  Skipped (built-in/app groups): {skipped}")
    print(f"  Okta-mastered groups: {len(okta_groups)}")
    print(f"  Non-compliant: {len(noncompliant)}\n")

    if not noncompliant:
        print("All groups follow the naming convention.")
        return

    print(f"Checking app assignments for {len(noncompliant)} non-compliant groups...")
    groups_with_apps = check_app_assignments(noncompliant)
    print(f"  Groups with app assignments: {len(groups_with_apps)}\n")

    print("Fetching group rules...")
    all_rules = get_all_group_rules()
    print(f"  Total rules: {len(all_rules)}")
    groups_in_rules = check_group_rules(all_rules, nc_ids)
    groups_as_target = {gid for gid, r in groups_in_rules.items() if r["target"]}
    groups_as_condition = {gid for gid, r in groups_in_rules.items() if r["condition"]}
    print(f"  Non-compliant groups as rule target: {len(groups_as_target)}")
    print(f"  Non-compliant groups as rule condition: {len(groups_as_condition)}\n")

    in_use_ids = set(groups_with_apps) | set(groups_in_rules)
    unused_ids = nc_ids - in_use_ids

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------------ #
    # Report 1: Non-compliant groups that ARE in use                       #
    # ------------------------------------------------------------------ #
    sep = "=" * 70
    if in_use_ids:
        print(sep)
        print(f"NON-COMPLIANT GROUPS IN USE  ({len(in_use_ids)} found)")
        print(sep)

        in_use_rows = []
        for gid in sorted(in_use_ids, key=lambda x: nc_by_id[x]["profile"]["name"].lower()):
            group = nc_by_id[gid]
            name = group["profile"]["name"]
            apps = groups_with_apps.get(gid, [])
            rules = groups_in_rules.get(gid, {})

            print(f"\nGroup : {name}")
            print(f"  ID  : {gid}")
            if apps:
                print(f"  Apps ({len(apps)}):")
                for a in apps:
                    print(f"    - {a}")
            target_rules = rules.get("target", []) if rules else []
            condition_rules = rules.get("condition", []) if rules else []

            if target_rules:
                print(f"  Target of rules ({len(target_rules)}):")
                for r in target_rules:
                    print(f"    - {r}")
            if condition_rules:
                print(f"  Used in rule conditions ({len(condition_rules)}):")
                for r in condition_rules:
                    print(f"    - {r}")

            in_use_rows.append({
                "group_name": name,
                "group_id": gid,
                "app_count": len(apps),
                "apps": "; ".join(apps),
                "target_rule_count": len(target_rules),
                "target_rules": "; ".join(target_rules),
                "condition_rule_count": len(condition_rules),
                "condition_rules": "; ".join(condition_rules),
            })

        csv_path = f"okta_noncompliant_inuse_{timestamp}.csv"
        write_csv(in_use_rows, csv_path, ["group_name", "group_id", "app_count", "apps", "target_rule_count", "target_rules", "condition_rule_count", "condition_rules"])
        print(f"\nIn-use report written to {csv_path}")
    else:
        print("No non-compliant groups are currently used in app assignments or group rules.")

    # ------------------------------------------------------------------ #
    # Report 2: Non-compliant groups with no apps, no rules, 0 members    #
    # Note: SAML attribute statements and sign-on policies are not checked #
    # ------------------------------------------------------------------ #
    if unused_ids:
        unused_groups = sorted(
            [nc_by_id[gid] for gid in unused_ids],
            key=lambda g: g["profile"]["name"].lower()
        )

        print(f"\n{sep}")
        print(f"POTENTIALLY UNUSED GROUPS  ({len(unused_groups)} with no apps, no rules)")
        print("NOTE: SAML attribute statements and sign-on policies are not checked.")
        print(sep)

        unused_rows = []
        for group in unused_groups:
            gid = group["id"]
            name = group["profile"]["name"]
            member_count = group.get("profile", {}).get("memberCount", "unknown")
            print(f"  {name}  ({gid})  members: {member_count}")
            unused_rows.append({
                "group_name": name,
                "group_id": gid,
                "member_count": member_count,
            })

        csv_path = f"okta_noncompliant_unused_{timestamp}.csv"
        write_csv(unused_rows, csv_path, ["group_name", "group_id", "member_count"])
        print(f"\nUnused report written to {csv_path}")


if __name__ == "__main__":
    main()
