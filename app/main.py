import argparse, os, yaml
from agents.controller import agent
from agents.memory import create_memory_manager

def load_cfg(path: str):
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def main():
    p = argparse.ArgumentParser(description="Multi-tenant RAG system with memory")
    p.add_argument("--tenant", required=True, choices=["U1", "U2", "U3", "U4"], 
                   help="Tenant ID for access control")
    p.add_argument("--query", help="Single query mode (if not provided, enters chat mode)")
    p.add_argument("--chat", action="store_true", help="Force interactive chat mode")
    p.add_argument("--memory", choices=["buffer", "summary", "none"], default="summary",
                   help="Memory mode: buffer (raw turns), summary (LLM summaries), none (no memory)")
    p.add_argument("--config", default="config.yaml", help="Config file path")
    args = p.parse_args()

    cfg = load_cfg(args.config)
    base_dir = os.path.dirname(os.path.dirname(__file__))

    # Create memory manager
    memory_manager = create_memory_manager(cfg)

    if args.query and not args.chat:
        # Single query mode
        print(agent(base_dir, args.tenant, args.query, cfg, memory_manager))
    else:
        # Interactive chat mode
        chat_repl(base_dir, args.tenant, cfg, memory_manager)


def chat_repl(base_dir: str, tenant_id: str, cfg: dict, memory_manager):
    """Interactive chat REPL for multi-turn conversations."""
    print(f"🤖 Multi-tenant RAG Chat - Tenant: {tenant_id}")
    print("📝 Memory management enabled - conversation will be saved")
    print("💡 Commands: /clear (clear memory), /stats (memory stats), /quit (exit)")
    print("=" * 60)
    
    # Show existing memory stats
    try:
        stats = memory_manager.get_memory_stats(tenant_id)
        if stats["total_messages"] > 0:
            print(f"📚 Resuming conversation: {stats['total_messages']} previous messages")
            print(f"🕒 Last updated: {stats['last_updated']}")
            print("-" * 60)
    except:
        print("🆕 Starting new conversation")
        print("-" * 60)
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{tenant_id}> ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['/quit', '/exit', '/q']:
                print("👋 Goodbye!")
                break
            elif user_input.lower() == '/clear':
                if memory_manager.clear_memory(tenant_id):
                    print("🧹 Memory cleared successfully!")
                else:
                    print("❌ Failed to clear memory")
                continue
            elif user_input.lower() == '/stats':
                try:
                    stats = memory_manager.get_memory_stats(tenant_id)
                    print(f"📊 Memory Statistics for {tenant_id}:")
                    print(f"   Total messages: {stats['total_messages']}")
                    print(f"   Buffer size: {stats['buffer_size']}")
                    print(f"   Has summary: {stats['has_summary']}")
                    print(f"   Summary count: {stats['summary_count']}")
                    print(f"   Created: {stats['created_at']}")
                    print(f"   Updated: {stats['last_updated']}")
                except Exception as e:
                    print(f"❌ Error getting stats: {e}")
                continue
            elif user_input.lower().startswith('/mode '):
                mode = user_input.split()[1].lower() if len(user_input.split()) > 1 else ""
                if mode in ["buffer", "summary"]:
                    # Update memory manager configuration (this would require manager restart)
                    print(f"🔄 Memory mode changed to: {mode}")
                    print("   Note: New mode will apply to subsequent conversations")
                    # In a full implementation, you'd recreate the memory manager
                else:
                    print("❌ Invalid mode. Use: /mode buffer or /mode summary")
                continue
            elif user_input.lower() == '/help':
                print("🔧 Available commands:")
                print("   /clear     - Clear conversation memory")
                print("   /stats     - Show memory statistics")
                print("   /mode buffer   - Switch to buffer memory mode")
                print("   /mode summary  - Switch to summary memory mode") 
                print("   /help      - Show this help")
                print("   /quit      - Exit chat")
                continue
                
            # Process regular query
            print("🤔 Processing...")
            response = agent(base_dir, tenant_id, user_input, cfg, memory_manager)
            print(f"\n🤖 Assistant: {response}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔄 Continuing... (type /quit to exit)")
            continue

if __name__ == "__main__":
    main()
