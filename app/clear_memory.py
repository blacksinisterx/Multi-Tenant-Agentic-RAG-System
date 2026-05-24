"""
AI-DOC:
Purpose: Clear conversation memory for specific tenants
Constraints: Tenant isolation, safe file operations
Manual QA: see plan.md -> Phase 4 Manual QA section
"""

import argparse
import yaml
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.memory import MemoryManager, create_memory_manager


def main():
    """Clear memory for a specific tenant."""
    ap = argparse.ArgumentParser(description="Clear conversation memory for a tenant")
    ap.add_argument("--tenant", required=True, help="Tenant ID (U1, U2, U3, U4)")
    ap.add_argument("--config", default="config.yaml", help="Config file path")
    ap.add_argument("--all", action="store_true", help="Clear memory for all tenants")
    args = ap.parse_args()
    
    # Load config
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        return
    except yaml.YAMLError as e:
        print(f"Error loading config: {e}")
        return
    
    # Create memory manager
    memory_manager = create_memory_manager(config)
    
    if args.all:
        # Clear all tenant memories
        tenants = memory_manager.list_tenants()
        if not tenants:
            print("No tenant memories found.")
            return
        
        print(f"Clearing memory for all tenants: {', '.join(tenants)}")
        cleared = 0
        for tenant in tenants:
            if memory_manager.clear_memory(tenant):
                print(f"✅ Cleared memory for {tenant}")
                cleared += 1
            else:
                print(f"❌ Failed to clear memory for {tenant}")
        
        print(f"\nCleared memory for {cleared}/{len(tenants)} tenants.")
    
    else:
        # Clear specific tenant memory
        tenant_id = args.tenant.upper()
        
        # Get stats before clearing
        try:
            stats = memory_manager.get_memory_stats(tenant_id)
            print(f"Memory stats for {tenant_id}:")
            print(f"  Total messages: {stats['total_messages']}")
            print(f"  Buffer size: {stats['buffer_size']}")
            print(f"  Has summary: {stats['has_summary']}")
            print(f"  Last updated: {stats['last_updated']}")
        except:
            print(f"No existing memory found for {tenant_id}")
        
        # Clear memory
        if memory_manager.clear_memory(tenant_id):
            print(f"✅ Successfully cleared memory for {tenant_id}")
        else:
            print(f"❌ Failed to clear memory for {tenant_id}")


if __name__ == "__main__":
    main()
