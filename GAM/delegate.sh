#!/bin/bash
# Interactive helper to delegate one Google Workspace mailbox to another via GAM.

set -euo pipefail

gam="$HOME/bin/gam7/gam"

echo ""
read -r -p "Enter the user to delegate FROM (email): " delegate_from
read -r -p "Enter the user to delegate TO (email): " delegate_to

echo ""
echo "You are about to run:"
echo "$gam user $delegate_from delegate to $delegate_to"
read -r -p "Proceed? [y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Cancelled. No changes made."
  exit 0
fi

echo ""
$gam user "$delegate_from" delegate to "$delegate_to"
echo "Delegation complete: $delegate_to can access $delegate_from"
