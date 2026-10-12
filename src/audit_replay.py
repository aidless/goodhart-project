"""B: 事后审计。重放 logs.jsonl 的判分, mismatch 必须为 0。"""
import json
import sys
from validators import Validator, classify_error

def main(logs="etl/results/logs.jsonl"):
    validator = Validator()
    mismatches = 0
    total_steps = 0

    with open(logs) as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            prev_valid = True
            for h in rec["steps"]:
                total_steps += 1
                re_valid = validator.check_step(rec["task_id"], h["k"], h["raw"])
                re_err = classify_error(prev_valid, re_valid)
                if re_valid != h["valid"] or re_err != h["err_type"]:
                    mismatches += 1
                    print(f"MISMATCH {rec['task_id']} k={h['k']}: "
                          f"logged=({h['valid']},{h['err_type']}) "
                          f"replay=({re_valid},{re_err})")
                prev_valid = re_valid

    print(f"审计完成: {total_steps} 步, mismatch={mismatches}")
    if mismatches > 0:
        print("FAIL — 判分不可复现, 结果作废")
        sys.exit(1)
    print("PASS — 判分可复现")

if __name__ == "__main__":
    # 可选位置参数: 日志路径 (默认 etl/results/logs.jsonl)。
    import sys as _sys
    main(_sys.argv[1] if len(_sys.argv) > 1 else "etl/results/logs.jsonl")