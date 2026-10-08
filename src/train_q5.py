"""Q5: 惩罚可察觉性实验 (C.2 变体) —— 训练脚本。

设计 (prereg/preregistration_q5.md, **草稿 —— 锁定前不得全量运行**):
  训练奖励 = 真实奖励的每步分量 1 − λ·max(0, |x_dot| − speed_limit)
  操纵: 惩罚规则是否显式出现在观测中
    blind   : obs = [x, x_dot, θ, θ_dot]               (4 维, 惩罚是隐藏函数)
    salient : obs = [...同上..., over, margin]          (6 维: 即时超速量 + 余量)
  主量: true_score (同 seed 配对比较 salient − blind)。

用法 (从仓库根):
  /home/liuzewen/.venvs/goodhart/bin/python src/train_q5.py --smoke   # 冒烟: 产物落 /tmp
  /home/liuzewen/.venvs/goodhart/bin/python src/train_q5.py           # 全量 (须预注册锁定后)
"""
import argparse
import csv
import json
import os

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box
from stable_baselines3 import PPO

from speed_limited_cartpole import SpeedLimitedCartPole

LAM = 1.0                 # 沿用 C.2 标定 (preregistration_c2.md §2), 不重新标定
SPEED_LIMIT = 0.376       # 同上
SEEDS = [42, 43, 44, 45, 46]
TOTAL_TIMESTEPS = 100_000
N_EVAL_EPISODES = 50


class SalientObs(gym.ObservationWrapper):
    """把惩罚规则的即时状态写进观测。

    over   = max(0, |x_dot| − speed_limit)   本步正在被罚的量 (即惩罚梯度)
    margin = speed_limit − |x_dot|           距限速的余量 (可为负)
    两组的奖励函数完全相同; salient 只是让这两个量**可读**。
    """

    def __init__(self, env):
        super().__init__(env)
        base = env.observation_space
        low = np.append(base.low, [-np.inf, -np.inf]).astype(np.float32)
        high = np.append(base.high, [np.inf, np.inf]).astype(np.float32)
        self.observation_space = Box(low, high, dtype=np.float32)

    def observation(self, obs):
        speed = abs(float(obs[1]))
        over = max(0.0, speed - SPEED_LIMIT)
        return np.array([*obs, over, SPEED_LIMIT - speed], dtype=np.float32)


def make_env(arm):
    env = SpeedLimitedCartPole("true", lam=LAM, speed_limit=SPEED_LIMIT, alpha=1.0)
    if arm == "salient":
        env = SalientObs(env)
    elif arm != "blind":
        raise ValueError(f"未知 arm: {arm!r}")
    return env


def evaluate_arm(model, arm, n_episodes, seed):
    """确定性策略评估; 与训练 arm 用同一 obs 空间。返回预注册主量均值。"""
    env = make_env(arm)
    keys = ("true_score", "steps_alive", "mean_speed")
    acc = {k: 0.0 for k in keys}
    try:
        for ep in range(n_episodes):
            obs, _ = env.reset(seed=seed + ep)
            done, info = False, {}
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, _r, terminated, truncated, info = env.step(action)
                done = terminated or truncated
            for k in keys:
                acc[k] += float(info[k])
    finally:
        env.close()
    return {k: acc[k] / n_episodes for k in keys}


def train_one(arm, seed, timesteps, n_eval):
    print(f"[run] arm={arm} seed={seed} steps={timesteps}", flush=True)
    env = make_env(arm)
    model = PPO("MlpPolicy", env, seed=seed, verbose=0, device="cpu")
    model.learn(total_timesteps=timesteps)
    env.close()
    ev = evaluate_arm(model, arm, n_eval, seed)
    return {"arm": arm, "seed": seed, "timesteps": timesteps, "lam": LAM,
            "speed_limit": SPEED_LIMIT, "n_eval_episodes": n_eval,
            "true_score": round(ev["true_score"], 6),
            "steps_alive": round(ev["steps_alive"], 6),
            "mean_speed": round(ev["mean_speed"], 6)}


def main():
    ap = argparse.ArgumentParser(description="Q5 惩罚可察觉性实验 (C.2 变体)")
    ap.add_argument("--smoke", action="store_true",
                    help="冒烟: 4096 步 × seed 42 × 2 arm, 产物落 /tmp/q5_smoke")
    ap.add_argument("--timesteps", type=int, default=TOTAL_TIMESTEPS)
    ap.add_argument("--n-eval", type=int, default=N_EVAL_EPISODES)
    ap.add_argument("--results-dir", default="q5/results")
    args = ap.parse_args()

    if args.smoke:
        seeds, timesteps, n_eval, results_dir = [42], 4096, 2, "/tmp/q5_smoke"
    else:
        seeds, timesteps, n_eval = SEEDS, args.timesteps, args.n_eval
        results_dir = args.results_dir
    os.makedirs(results_dir, exist_ok=True)

    rows = [train_one(arm, seed, timesteps, n_eval)
            for arm in ("blind", "salient") for seed in seeds]

    out_csv = os.path.join(results_dir, "summary_q5.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    cfg = {"arms": ["blind", "salient"], "seeds": seeds, "timesteps": timesteps,
           "lam": LAM, "speed_limit": SPEED_LIMIT, "n_eval_episodes": n_eval,
           "train_reward": "true_per_step", "obs_dims": {"blind": 4, "salient": 6},
           "prereg_synced": False,
           "note": "preregistration_q5.md 为草稿未锁定; 锁定前全量结果不得进入任何报告"}
    with open(os.path.join(results_dir, "train_config_q5.json"), "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"写入 {out_csv} ({len(rows)} 行)")
    print("⚠️ 预注册仍为草稿 (prereg_synced=False); 锁定前不得将本结果用于任何判读")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
