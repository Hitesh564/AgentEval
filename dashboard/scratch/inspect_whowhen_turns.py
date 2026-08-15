from datasets import load_dataset

def main():
    ds = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")["train"]
    for i in range(15):
        item = ds[i]
        q_id = str(item["question_ID"])
        roles = [step.get("role") for step in item["history"] if step.get("role") != "human"]
        print(f"Case {i+1:2d} ({q_id[:8]}...): Mistake Agent={item['mistake_agent']:<15} | Turn Sequence: {roles}")

if __name__ == "__main__":
    main()
