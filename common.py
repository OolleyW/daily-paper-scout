#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享工具：配置加载、Server酱微信通知、启发式摘要分析（LLM 失败时的兜底）。"""
import json
import os
import re

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def notify(cfg, title, desp):
    sendkey = cfg.get("serverchan", {}).get("sendkey", "")
    if not sendkey:
        print("未配置 Server酱 SendKey，跳过通知")
        return
    try:
        r = requests.post(
            f"https://sctapi.ftqq.com/{sendkey}.send",
            data={"title": title, "desp": desp[:32000]},
            timeout=30,
        )
        data = r.json()
        if data.get("code") == 0:
            print(f"ServerChan 通知成功 pushid={data.get('data', {}).get('pushid')}")
        else:
            print(f"ServerChan 通知失败: {data}")
    except Exception as e:
        print(f"ServerChan 通知异常: {e}")


METHOD_HINTS = [
    "finite element", "fem", "experiment", "experimental", "numerical", "analytical",
    "simulation", "model", "machine learning", "deep learning", "neural network",
    "algorithm", "framework", "based on", "using", "develop", "proposed", "specimen",
    "monte carlo", "optimization", "test", "benchmark", "dataset", "regression",
    "convolutional", "genetic", "surrogate", "digital twin", "bim", "computer vision",
]
RESULT_HINTS = [
    "result", "show", "found", "finding", "indicate", "demonstrate", "reveal",
    "compare", "improve", "reduc", "increas", "decreas", "higher", "lower", "better",
    "accuracy", "error", "outperform", "conclud", "conclusion", "valid", "effective",
    "enhance", "predict", "achieve", "superior", "significan",
]


def _split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]


def heuristic_analysis(abstract):
    sents = _split_sentences(abstract)
    objective, methods, conclusions = [], [], []
    n = len(sents)
    for i, s in enumerate(sents):
        low = s.lower()
        if i <= 1 and ("this paper" in low or "this study" in low or "aim" in low
                       or "investigate" in low or "propose" in low or "study" in low):
            objective.append(s)
        if any(h in low for h in METHOD_HINTS):
            methods.append(s)
        if any(h in low for h in RESULT_HINTS):
            conclusions.append(s)
    if not objective:
        objective = sents[:1]
    if not methods:
        methods = sents[: min(2, n)]
    if not conclusions:
        conclusions = sents[max(0, n - 2):]
    return {
        "objective": " ".join(objective[:3]),
        "methods": " ".join(methods[:4]),
        "conclusions": " ".join(conclusions[:4]),
    }
