"""C.2 Goodhart 脱钩实验: CartPole + PPO, 真实奖励 vs 代理奖励。

★ 本文件的超参数尚未与 preregistration_c2.md 核对。所有标
  `# PREREG-SYNC` 的行都是占位值, 必须逐条对齐预注册后才可用于正式实验。

输出: c2/results/summary.csv, 列与 analyze_c2.py 期望的格式一致。
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

# PREREG-SYNC: 依赖 sb3 (stable-baselines3)。若本机未装, 见 requirements.txt。
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

# ---------------------------------------------------------------------------
# 实验配置 —— 全部待与预注册核对
# ---------------------------------------------------------------------------
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]        # PREREG-SYNC: 代理权重的扫描网格
SEEDS = [0, 1, 2, 3, 4]                      # PREREG-SYNC: 种子数
TOTAL_TIMESTEPS = 100_000                    # PREREG-SYNC: 每条件训练步数
N_EVAL_EPISODES = 50                         # PREREG-SYNC: 评估回合数
PROXY_KIND = "cartpole_x_pos"                # PREREG-SYNC: 代理目标定义

OUT_DIR = os.path.join("c2", "results")
SUMMARY_CSV = os.path.join(OUT_DIR, "summary.csv")

def set_seed(seed: int) -> None:
    """固定全部随机源。任何一处漏了都会让种子不可复现。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def proxy_reward(obs: np.ndarray, true_reward: float, alpha: float) -> float:
    """真实奖励与代理奖励的凸组合。

    代理 = 小车向右的位置 (obs[0])。这是 CartPole 里最经典的 Goodhart 代理:
    优化它会把策略推向「往右冲」而非「撑得久」。
    PREREG-SYNC: 代理定义与 alpha 混合形式必须与预注册一致。
    """
    if PROXY_KIND == "cartpole_x_pos":
        proxy = float(obs[0])
    else:
        raise ValueError(f"未实现的代理类型: {PROXY_KIND}")
    return (1.0 - alpha) * true_reward + alpha * proxy

class ProxyRewardWrapper:
    """把环境包一层, 用 proxy_reward 替换 reward。

    不用 gym.Wrapper 子类, 是为了避免版本差异 (gym vs gymnasium) 带来的
    `reset` 签名不兼容 —— 只转发我们用到的两个方法。
    """

    def __init__(self, env, alpha: float):
        self.env = env
        self.alpha = alpha

    def reset(self, **kwargs):
        out = self.env.reset(**kwargs)
        # gym 老版返回 obs, gymnasium 返回 (obs, info)
        if isinstance(out, tuple):
            obs, info = out
            return obs, info
        return out

    def step(self, action):
        out = self.env.step(action)
        if len(out) == 5:                    # gymnasium: obs, r, term, trunc, info
            obs, r, terminated, truncated, info = out
            r = proxy_reward(obs, r, self.alpha)
            return obs, r, terminated, truncated, info
        obs, r, done, info = out             # gym 老版: obs, r, done, info
        r = proxy_reward(obs, r, self.alpha)
        return obs, r, done, info

    def __getattr__(self, name):
        return getattr(self.env, name)

def evaluate_true_return(model, seed: int, n_episodes: int) -> float:
    """在【真实】奖励上评估, 与训练时的代理奖励无关。

    这是 C.2 的核心测量口: 代理优化得再好, 真实回报是否掉下去。
    """
    env = build_env(alpha=0.0)  # alpha=0 → 纯真实奖励
    mean_r, _ = evaluate_policy(
        model, env, n_eval_episodes=n_episodes, deterministic=True,
        warn=False,
    )
    env.close()
    return float(mean_r)

def build_env(alpha: float):
    """构建被包装的 CartPole 环境。"""
    import gymnasium as gym
    raw = gym.make("CartPole-v1")
    if alpha != 0.0:
        raw = ProxyRewardWrapper(raw, alpha)
    return raw

def run_one(alpha: float, seed: int, timesteps: int) -> dict:
    """跑单个 (alpha, seed) 条件, 返回一行结果。"""
    set_seed(seed)
    env = build_env(alpha)
    model = PPO(
        "MlpPolicy", env,
        seed=seed,
        verbose=0,
        # PREREG-SYNC: 以下超参若预注册有钉死值, 必须改成显式传参
        n_steps=1024, batch_size=64, gamma=0.99, learning_rate=3e-4,
    )
    model.learn(total_timesteps=timesteps)
    env.close()

    true_return = evaluate_true_return(model, seed, N_EVAL_EPISODES)

    return {
        "alpha": alpha,
        "seed": seed,
        "timesteps": timesteps,
        "proxy_kind": PROXY_KIND,
        "true_return_mean": round(true_return, 4),
        # PREREG-SYNC: 若预注册要求记录代理回报/偏离度等, 在此追加列
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
        "proxy_kind": PROXY_KIND, "n_eval_episodes": N_EVAL_EPISODES,
        "prereg_synced": False,
    }
    with open(os.path.join(OUT_DIR, "train_config.json"), "w",
              encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"写入 {SUMMARY_CSV} ({len(rows)} 行)")
    print(f"summary.csv sha256 = {file_sha256(SUMMARY_CSV)}")
    print("提醒: prereg_synced=False, 请先与预注册核对再用于正式实验。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
