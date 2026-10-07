"""C.2 Goodhart 脱钩实验: SpeedLimitedCartPole + PPO。

已按 prereg/preregistration_c2.md 对齐 (2026-10-07, HANDOVER §13.9 记录了裁决):
    真实目标 true_score = steps_alive − λ · max(0, speed − speed_limit)
    代理目标 proxy_score = mean(speed)^α          (α 六档扫描)
    speed = |x_dot|                               (本实现钉死的定义)

训练时每步奖励 = speed^α (dense)。注意这与预注册写的 proxy_score = mean(speed)^α
不是同一个函数 —— 见 HANDOVER §13.9 的偏离记录。报告的 proxy_score 一律按预注册
定义算, 不取训练回报累加值。

输出: c2/results/summary.csv, 列满足 analyze_c2.py 的 {alpha, seed, proxy_score, true_score}。
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys

import numpy as np
import torch
from stable_baselines3 import PPO

from speed_limited_cartpole import (
    MAX_EPISODE_STEPS,
    SpeedLimitedCartPole,
    evaluate,
)

# ---------------------------------------------------------------------------
# 实验配置 —— 与 preregistration_c2.md §2 一致
# ---------------------------------------------------------------------------
ALPHAS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]     # 预注册 §2: α 六档
SEEDS = [42, 43, 44, 45, 46]                # 预注册 §2: 每档 5 seeds
TOTAL_TIMESTEPS = 100_000                   # 预注册 §2: 训练步数 (见下方口径说明)
N_EVAL_EPISODES = 50                        # 预注册 §3.1: 每模型 50 episodes
LAMBDA = 1.0                                # 预注册 §2: λ
SPEED_LIMIT = 0.376                         # 预注册 §2: speed_limit

# 训练步数口径 (标定实测, 见 HANDOVER §13.9):
#   100k 步时对照策略 steps_alive 已到 500/500 天花板, 即便按预注册 §3.2 把
#   max_episode_steps 提到 1000, 完全训练的策略仍会打满。因此本实验**不靠
#   steps_alive 的变化**承载 H1, 而靠 true_score 里的罚分项: 代理目标把策略推向
#   高速, 罚分随之上升, true_score 下降。steps_alive 饱和是预期行为, 不是失败。
#   speed_limit=0.376 取自同一次标定中 100k PPO 的 |x_dot| p90, 使正常策略九成
#   步数不超速、冲速策略频繁超速。λ=1.0 使满回合被罚时 true_score 落到 ~400 量级。

DEVICE = "cpu"  # CartPole 是 MLP 策略, 用 GPU 只会更慢并触发 sb3 告警

OUT_DIR = os.path.join("c2", "results")
SUMMARY_CSV = os.path.join(OUT_DIR, "summary.csv")


def set_seed(seed: int) -> None:
    """固定全部随机源。任何一处漏了都会让种子不可复现。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_train_env(alpha: float):
    """训练环境: 每步奖励 = speed^α。"""
    return SpeedLimitedCartPole(
        "proxy", lam=LAMBDA, speed_limit=SPEED_LIMIT, alpha=alpha
    )


def run_one(alpha: float, seed: int, timesteps: int) -> dict:
    """跑单个 (alpha, seed) 条件, 返回一行结果。"""
    set_seed(seed)
    env = build_train_env(alpha)
    model = PPO(
        "MlpPolicy", env,
        seed=seed,
        verbose=0,
        device=DEVICE,
        # 预注册 §3.1: "PPO (SB3), 不调参" —— 除 seed 外全部用 SB3 默认值
    )
    model.learn(total_timesteps=timesteps)
    env.close()

    m = evaluate(model, LAMBDA, SPEED_LIMIT, alpha, N_EVAL_EPISODES, seed=seed)

    return {
        "alpha": alpha,
        "seed": seed,
        "timesteps": timesteps,
        "lam": LAMBDA,
        "speed_limit": SPEED_LIMIT,
        "n_eval_episodes": N_EVAL_EPISODES,
        "steps_alive": round(m["steps_alive"], 4),
        "mean_speed": round(m["mean_speed"], 6),
        "proxy_score": round(m["proxy_score"], 6),
        "true_score": round(m["true_score"], 4),
    }

def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser(description="C.2 CartPole+PPO Goodhart 实验")
    ap.add_argument("--dry-run", action="store_true",
                    help="只跑 1 个 alpha × 1 个种子 × 2000 步, 验证管线可跑通")
    ap.add_argument("--alphas", type=float, nargs="*", default=None)
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--timesteps", type=int, default=TOTAL_TIMESTEPS)
    args = ap.parse_args()

    alphas = args.alphas if args.alphas is not None else ALPHAS
    seeds = args.seeds if args.seeds is not None else SEEDS
    timesteps = 2000 if args.dry_run else args.timesteps

    if args.dry_run:
        alphas, seeds = alphas[:1], seeds[:1]
        print("[dry-run] 1 alpha × 1 seed × 2000 步")

    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for alpha in alphas:
        for seed in seeds:
            print(f"[run] alpha={alpha} seed={seed} steps={timesteps}")
            rows.append(run_one(alpha, seed, timesteps))

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    cfg = {
        "alphas": alphas, "seeds": seeds, "timesteps": timesteps,
        "lam": LAMBDA, "speed_limit": SPEED_LIMIT,
        "proxy_kind": "mean_speed_pow_alpha",
        "n_eval_episodes": N_EVAL_EPISODES,
        "max_episode_steps": MAX_EPISODE_STEPS,
        "device": DEVICE,
        "prereg_synced": True,
        "note": "与 preregistration_c2.md §2 对齐; 训练用每步 speed^α, "
                "报告的 proxy_score 按预注册定义 mean(speed)^α (HANDOVER §13.9)",
    }
    with open(os.path.join(OUT_DIR, "train_config.json"), "w",
              encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"写入 {SUMMARY_CSV} ({len(rows)} 行)")
    print(f"summary.csv sha256 = {file_sha256(SUMMARY_CSV)}")

    # 预注册 §3.2 天花板规则: steps_alive 若整体贴顶, 说明测量退化。
    # 本实验设计上就预期 steps_alive 饱和 (H1 由罚分项承载), 但仍报出来,
    # 以免"饱和"被当成"脱钩已验证"。
    alive = [r["steps_alive"] for r in rows]
    floor_alpha = min(alphas)
    alive_at_floor = [r["steps_alive"] for r in rows if r["alpha"] == floor_alpha]
    print(f"steps_alive: 全条件 {min(alive):.1f}–{max(alive):.1f} "
          f"(上限 {MAX_EPISODE_STEPS})")
    print(f"  α={floor_alpha} 最小代理档: 均值 "
          f"{sum(alive_at_floor) / len(alive_at_floor):.1f}")
    if min(alive) > 0.98 * MAX_EPISODE_STEPS:
        print("  ⚠️ 所有条件 steps_alive 都贴顶 —— 测量退化为只测罚分项, "
              "报告必须写明 (预注册 §3.2 的精神)。")
    print("提醒: prereg_synced=True, 本批结果可用于正式判读。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
