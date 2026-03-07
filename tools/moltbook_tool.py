import os
import requests
import json
import time

class MoltbookTool:
    """
    Moltbook APIを使用した投稿および検証ツール。
    """
    @staticmethod
    def post(text: str):
        api_key = os.getenv("MOLTBOOK_API_KEY")
        if not api_key:
            print("Error: MOLTBOOK_API_KEY not found.")
            return False

        url = "https://www.moltbook.com/api/v1/posts"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "submolt_name": "all",
            "title": text[:300],
            "content": text
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            data = response.json()
            
            if response.status_code == 200 or response.status_code == 201:
                # 既に信頼されている場合は即完了
                if not data.get("verification_required"):
                    print("Successfully posted (Immediate).")
                    return True
                
                # 検証が必要な場合 (AI Verification)
                print("Verification required. Solving challenge...")
                verification = data.get("post", {}).get("verification", {})
                v_code = verification.get("verification_code")
                challenge = verification.get("challenge_text")
                
                if not v_code or not challenge:
                    print(f"Error: Missing verification data. {data}")
                    return False
                
                # 司令官（Neo）がパズルを解くロジック
                answer = MoltbookTool.solve_challenge(challenge)
                if not answer:
                    print("Error: Could not solve challenge.")
                    return False
                
                print(f"Challenge solved: {answer}. Submitting...")
                
                # 検証リクエスト
                v_url = "https://www.moltbook.com/api/v1/verify"
                v_payload = {
                    "verification_code": v_code,
                    "answer": answer
                }
                v_response = requests.post(v_url, headers=headers, json=v_payload, timeout=10)
                v_data = v_response.json()
                
                if v_response.status_code == 200 and v_data.get("success"):
                    print("Verification successful! Post published.")
                    return True
                else:
                    print(f"Verification failed: {v_data}")
                    return False
            else:
                print(f"Post failed ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return False

    @staticmethod
    def solve_challenge(challenge_text: str) -> str:
        """
        難読化された数学パズルを解く。
        例: "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fI[vE"
        """
        # 司令官(Neo)自身のLLMを使用してパズルを解くのが最も確実
        from core.config import get_neo_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        
        llm = get_neo_llm()
        prompt = f"""
Solve the following obfuscated math word problem. 
The text contains alternating caps, scattered symbols, and broken words.
Extract the two numbers and the operation, calculate the result, and respond with ONLY the numeric answer formatted with two decimal places (e.g., '15.00').

Challenge Text: {challenge_text}
"""
        try:
            response = llm.invoke([
                SystemMessage(content="You are a math solver specialized in de-obfuscating word problems."),
                HumanMessage(content=prompt)
            ])
            answer = response.content.strip()
            # 数字のみを抽出 (念のため)
            import re
            match = re.search(r"(-?\d+\.\d+)", answer)
            return match.group(1) if match else answer
        except Exception as e:
            print(f"Failed to solve challenge via LLM: {e}")
            return None
