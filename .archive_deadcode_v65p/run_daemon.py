import time
from neo_main import NeoSystem

if __name__ == "__main__":
    print("===================================================")
    print(" 👁️ NeoSystem Daemon: Infinite Surveillance Started ")
    print("===================================================")
    
    neo = NeoSystem()
    
    cycle_count = 1
    while True:
        print(f"\n>>> Starting Surveillance Cycle #{cycle_count} <<<")
        neo.autonomous_post_cycle(topic="VIRTUAL市場の急変動検知")
        
        print("\n[Daemon] Cycle complete. Entering sleep mode for 5 minutes (300s)...")
        print("Press [Ctrl+C] to terminate the daemon.")
        time.sleep(300)  # 5分間待機
        cycle_count += 1
