import json
from agents.paper_trader import PaperTraderAgent
from tools.paper_wallet import PaperWallet

def test_paper_trading():
    print("🚀 Starting Paper Trader Test Run...")
    
    # 1. Instantiate Agent
    agent = PaperTraderAgent()
    
    # 2. Check Initial Balance
    initial_balance = agent.wallet.get_balance()
    print(f"💰 Initial USD Balance: ${initial_balance:,.2f}")
    
    # 3. Create Mock Strategy (BUY Signal)
    # This simulates what PlanningCrew would output
    mock_strategy_buy = {
        "virtuals_payload": {
            "risk_policy": {
                "max_ltv": 0.7, # High LTV triggers "Risk On" (BUY)
                "min_credit_rating": "B"
            },
            "action_directive": "Aggressive accumulation of VIRTUAL token."
        }
    }
    
    print("\n📋 Executing BUY Strategy (Max LTV: 0.7)...")
    result_buy = agent.execute_strategy(mock_strategy_buy)
    print(f"✅ Execution Result: {json.dumps(result_buy, indent=2)}")
    
    # 4. Check Updated Wallet
    updated_balance = agent.wallet.get_balance()
    holdings = agent.wallet.get_holding("VIRTUAL")
    print(f"💰 Updated USD Balance: ${updated_balance:,.2f}")
    print(f"📦 VIRTUAL Holdings: {holdings:,.4f}")
    
    if holdings > 0 and updated_balance < initial_balance:
        print("\n🎉 Test Success: Buy order executed and wallet updated.")
    else:
        print("\n❌ Test Failed: Wallet state did not change as expected.")

if __name__ == "__main__":
    try:
        test_paper_trading()
    except Exception as e:
        print(f"\n❌ Critical Error during test: {e}")
        import traceback
        traceback.print_exc()
