"""B: 单向流验证器。只读 schedules, 输出真正的判分, 不泄露真值。"""
import pickle

class Validator:
    """验证器持有 schedules; 模型侧永远拿不到。"""

    def __init__(self, schedules_path="etl/data/schedules/schedules.pkl"):
        with open(schedules_path, "rb") as f:
            self.schedules = pickle.load(f)

    def check_step(self, task_id, k, model_answer):
        """判第 k步 (0-indexed)。返回 valid: bool。
        err_type 由 classify_error 结合 prev_valid 决定。"""
        s = self.schedules[task_id]
        truth = s["truth_chain"][k]
        fam = s["family"]

        try:
            if fam == "stateful-calc":
                ok = int(str(model_answer).strip()) == truth
            elif fam == "chain-sort":
                got = [int(x) for x in str(model_answer).replace(" ", "").split(",")]
                ok = got == truth
            elif fam == "ret-path":
                ok = int(str(model_answer).strip()) == truth
            else:
                ok = False
        except Exception:
            ok = False
        return ok

    def n_steps(self, task_id):
        return self.schedules[task_id]["n_steps"]

def classify_error(prev_valid, cur_valid):
    """误差类型分类。
    prev_valid=True 且 cur_valid=False → 'single' (单步独立错)
    prev_valid=False 且 cur_valid=False → 'cumulative' (带病继续)
    """
    if cur_valid:
        return None
    return "single" if prev_valid else "cumulative"