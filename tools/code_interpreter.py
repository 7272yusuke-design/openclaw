import subprocess
import json
import sys
import os
import time

def run_code(code: str, timeout: int = 30):
    """
    隔離されたサブプロセスでPythonコードを実行し、結果をJSONで返す。
    """
    # 一時ファイルの作成
    temp_file = "temp_exec.py"
    with open(temp_file, "w") as f:
        f.write(code)
    
    start_time = time.time()
    try:
        process = subprocess.Popen(
            [sys.executable, temp_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = -1
            stderr += f"\n[Error] Execution timed out after {timeout} seconds."
            
    except Exception as e:
        stdout = ""
        stderr = str(e)
        exit_code = -1
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    execution_time = time.time() - start_time
    
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "execution_time_sec": round(execution_time, 4)
    }

if __name__ == "__main__":
    # 直接実行された場合の簡単なテスト
    test_code = "print('Interpreter Online')"
    print(json.dumps(run_code(test_code), indent=2))
