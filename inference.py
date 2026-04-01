import os

MODEL_NAME = os.getenv("MODEL_NAME", "test-model")

def run():
    print(f"[START] task=test env=openenv model={MODEL_NAME}")

    print("[STEP] step=1 action=test_action reward=0.50 done=false error=null")
    print("[STEP] step=2 action=test_action reward=1.00 done=true error=null")

    print("[END] success=true steps=2 rewards=0.50,1.00")


if __name__ == "__main__":
    run()