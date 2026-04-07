from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response
import requests
import os
import json
import re
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY") or \
    (_ for _ in ()).throw(
        RuntimeError("DASHBOARD_SECRET_KEY environment variable not set")
    )
EMERGENCY_INCIDENTS = []

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5001/api")
HEALTH_URL = os.environ.get("HEALTH_URL", "http://localhost:5001/health")

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Proactive Sentinel - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e8edf5;
        }
        .login-card {
            width: min(420px, 92vw);
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.10);
            backdrop-filter: blur(12px);
            border-radius: 24px;
            padding: 34px;
            box-shadow: 0 16px 36px rgba(0,0,0,0.35);
        }
        .brand { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }
        .brand-mark {
            width: 28px; height: 28px; border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.18);
            display: grid; place-items: center; color: #d7def0;
        }
        h2 { font-size: 20px; font-weight: 600; color: #f4f7ff; }
        .sub { color: #9aa4b8; font-size: 13px; margin-bottom: 12px; }
        input {
            width: 100%; padding: 12px 14px; margin: 10px 0;
            border-radius: 12px; border: 1px solid rgba(255,255,255,0.18);
            background: rgba(255,255,255,0.08); color: #f4f7ff; font-size: 14px; outline: none;
        }
        input:focus {
            border-color: rgba(0,212,170,0.55);
            box-shadow: 0 0 0 3px rgba(0,212,170,0.15);
        }
        input::placeholder { color: rgba(255,255,255,0.45); }
        button {
            width: 100%; margin-top: 12px; padding: 12px;
            border: none; border-radius: 999px; cursor: pointer;
            background: #00d4aa; color: #08131a; font-weight: 700; font-size: 15px;
        }
        .error { color: #ff6b81; text-align: center; margin-top: 14px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand">
            <div class="brand-mark" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.2"></rect>
                    <rect x="5.2" y="4.4" width="1.1" height="2.3" rx="0.3" fill="currentColor"></rect>
                    <rect x="7.7" y="4.4" width="1.1" height="2.3" rx="0.3" fill="currentColor"></rect>
                </svg>
            </div>
            <h2>Proactive Sentinel</h2>
        </div>
        <div class="sub">Sign in to access the SOC dashboard.</div>
        <form method="POST" action="/login">
            <input type="email" name="email" placeholder="admin@acme.com" required>
            <input type="password" name="password" placeholder="password" required>
            <button type="submit">Login</button>
        </form>
        {% with messages = get_flashed_messages() %}
            {% for message in messages %}
                <div class="error">{{ message }}</div>
            {% endfor %}
        {% endwith %}
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Proactive Sentinel - SOC Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117;
            color: #e8edf5;
        }
        body.posture-clean { box-shadow: inset 0 0 200px rgba(0,212,170,0.08); }
        body.posture-elevated { box-shadow: inset 0 0 220px rgba(255,140,66,0.10); }
        body.posture-critical { box-shadow: inset 0 0 260px rgba(255,71,87,0.12); }
        .app-container { display: flex; min-height: 100vh; }
        .sidebar {
            width: 260px; position: fixed; height: 100vh; overflow-y: auto;
            background: rgba(10,10,18,0.92);
            border-right: 1px solid rgba(255,255,255,0.08);
            backdrop-filter: blur(12px);
            padding: 20px 0;
        }
        .logo {
            display: flex; align-items: center; gap: 10px;
            margin: 0 18px 18px; padding: 0 6px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .logo-badge {
            width: 28px; height: 28px; border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.18);
            display: grid; place-items: center; color: #d7def0;
        }
        .logo-text { color: #f8fafc; font-weight: 600; font-size: 15px; }
        .nav-item {
            display: block; text-decoration: none; color: #9ca3af;
            padding: 12px 24px; margin: 4px 10px; border-radius: 10px;
            border: 1px solid transparent; transition: all 0.2s ease;
        }
        .nav-item:hover, .nav-item.active {
            color: #d7def0;
            border-color: rgba(0,212,170,0.45);
            background: rgba(0,212,170,0.10);
            box-shadow: 0 0 0 1px rgba(0,212,170,0.20), 0 0 20px rgba(0,212,170,0.12);
        }
        .main-content { margin-left: 260px; flex: 1; padding: 24px 28px; }
        .top-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding-bottom: 16px; margin-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .popia-badge {
            border: 1px solid rgba(0,212,170,0.45);
            color: #00d4aa;
            font-size: 11px;
            border-radius: 999px;
            padding: 5px 10px;
            background: rgba(0,212,170,0.10);
            font-family: 'JetBrains Mono', monospace;
        }
        .utc, .user-email, .footer { font-family: 'JetBrains Mono', monospace; }
        .utc { color: #8b95a8; font-size: 12px; }
        .clock-stack { display: grid; gap: 3px; }
        .clock-line {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #b6c0d3;
        }
        .clock-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #7f8aa2;
            letter-spacing: .7px;
        }
        .user-info { display: flex; align-items: center; gap: 12px; }
        .user-email { font-size: 13px; color: #a9b4c8; }
        .live-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #00d4aa;
            border: 1px solid rgba(0,212,170,0.35);
            border-radius: 999px;
            padding: 4px 9px;
            background: rgba(0,212,170,0.10);
        }
        .live-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00d4aa;
            box-shadow: 0 0 8px #00d4aa;
            animation: livePulse 1.5s ease-in-out infinite;
        }
        .live-status.offline {
            color: #ff4c4c;
            border-color: rgba(255,76,76,0.4);
            background: rgba(255,76,76,0.10);
        }
        .live-status.offline .live-dot {
            background: #ff4c4c;
            box-shadow: 0 0 0 transparent;
            animation: none;
        }
        @keyframes livePulse {
            0%, 100% { opacity: .45; box-shadow: 0 0 4px #00d4aa; }
            50% { opacity: 1; box-shadow: 0 0 12px #00d4aa; }
        }
        .logout-btn {
            text-decoration: none; padding: 8px 14px; border-radius: 999px;
            background: #00d4aa; color: #08131a; font-size: 12px; font-weight: 700;
        }
        .threat-map, .stat-card, .alert-card {
            background: rgba(22,27,39,0.72);
            border: 1px solid rgba(255,255,255,0.08);
            backdrop-filter: blur(12px);
        }
        .bento-grid {
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 14px;
        }
        .hero-tile { grid-column: 1 / 9; }
        .ops-tile { grid-column: 9 / 13; }
        .signals-tile { grid-column: 1 / 7; }
        .popia-tile { grid-column: 7 / 13; }
        .alerts-tile { grid-column: 1 / 13; }
        .logs-tile { grid-column: 1 / 13; }
        .hover-expand { transition: transform .2s ease, box-shadow .2s ease; }
        .hover-expand:hover { transform: translateY(-2px) scale(1.01); box-shadow: 0 0 0 1px rgba(0,212,170,0.26), 0 0 26px rgba(0,212,170,0.18); }
        .threat-map { border-radius: 16px; padding: 22px; margin-bottom: 18px; }
        .gov-ticker {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .ticker-item {
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            text-align: center;
            background: rgba(255,255,255,0.03);
        }
        .ticker-item.safe { color: #00d4aa; border-color: rgba(0,212,170,0.4); }
        .ticker-item.warn { color: #ff8c42; border-color: rgba(255,140,66,0.45); }
        .ticker-item.risk { color: #ff4757; border-color: rgba(255,71,87,0.5); }
        .market-wrap { margin-top: 12px; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 10px; background: rgba(0,0,0,0.18); }
        #threat-market-chart { min-height: 250px; }
        .threat-map-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .threat-map-title { font-size: 12px; letter-spacing: 1.4px; color: #8b95a8; text-transform: uppercase; }
        .elevated-badge {
            padding: 5px 11px; border-radius: 999px; font-size: 11px;
            border: 1px solid rgba(255,140,66,0.45);
            color: #ff8c42; background: rgba(255,140,66,0.12);
        }
        .company-name { font-size: 25px; font-weight: 700; margin-bottom: 7px; }
        .company-desc { color: #9ca3af; font-size: 14px; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
        .stat-card { border-radius: 14px; padding: 18px; transition: box-shadow 0.2s ease; }
        .stat-card:hover, .alert-card:hover { box-shadow: 0 0 0 1px rgba(0,212,170,0.25), 0 0 24px rgba(0,212,170,0.18); }
        .stat-card h3 { font-size: 12px; letter-spacing: 1.1px; text-transform: uppercase; color: #8b95a8; margin-bottom: 10px; }
        .status-badge {
            display: inline-block; padding: 6px 11px; border-radius: 999px; font-size: 12px;
            border: 1px solid rgba(0,212,170,0.45); background: rgba(0,212,170,0.11); color: #00d4aa;
        }
        .signal-sources { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
        .signal-tag {
            padding: 6px 12px; border-radius: 999px; font-size: 12px; color: #b6c0d3;
            border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.03);
        }
        .alerts-section h2 {
            margin: 6px 0 14px; font-size: 15px; letter-spacing: 1px;
            color: #a8b3c8; text-transform: uppercase;
        }
        .section-title {
            margin: 14px 0 12px; font-size: 14px; letter-spacing: 1px;
            color: #a8b3c8; text-transform: uppercase;
        }
        .arch-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 14px;
        }
        .arch-item {
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
            padding: 12px;
        }
        .arch-name { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .8px; }
        .arch-value { margin-top: 6px; font-size: 13px; color: #e8edf5; font-weight: 600; }
        .health-list {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 12px;
        }
        .health-pill {
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 11px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.14);
            font-family: 'JetBrains Mono', monospace;
        }
        .health-pill.ok {
            color: #00d4aa;
            background: rgba(0,212,170,0.10);
            border-color: rgba(0,212,170,0.35);
        }
        .health-pill.bad {
            color: #ff8c42;
            background: rgba(255,140,66,0.10);
            border-color: rgba(255,140,66,0.35);
        }
        .health-pill.critical {
            color: #ff4757;
            background: rgba(255,71,87,0.12);
            border-color: rgba(255,71,87,0.40);
        }
        .pulse-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .pulse-item {
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
            padding: 10px;
            font-size: 11px;
        }
        .robot-dot {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            margin-bottom: 6px;
            border: 1px solid rgba(255,255,255,0.25);
            animation: robotPulse 1.6s ease-in-out infinite;
        }
        .robot-green { background: #00d4aa; box-shadow: 0 0 14px rgba(0,212,170,0.55); }
        .robot-amber { background: #ffb347; box-shadow: 0 0 14px rgba(255,179,71,0.55); }
        .robot-red { background: #ff4c4c; box-shadow: 0 0 16px rgba(255,76,76,0.65); animation-duration: .8s; }
        @keyframes robotPulse {
            0%, 100% { transform: scale(1); opacity: .9; }
            50% { transform: scale(1.15); opacity: 1; }
        }
        .pulse-label { color: #9ca3af; }
        .pulse-value { margin-top: 4px; font-family: 'JetBrains Mono', monospace; color: #d7deed; }
        .pulse-item.amber {
            border-color: rgba(255,140,66,0.45);
            box-shadow: 0 0 0 1px rgba(255,140,66,0.22), 0 0 24px rgba(255,140,66,0.14);
        }
        .pulse-item.red {
            border-color: rgba(255,76,76,0.50);
            box-shadow: 0 0 0 1px rgba(255,76,76,0.28), 0 0 26px rgba(255,76,76,0.18);
        }
        .commentary-box {
            margin-top: 8px;
            padding: 8px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            color: #b8c2d6;
        }
        .masking-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
        .masking-table th, .masking-table td { border-bottom: 1px solid rgba(255,255,255,0.08); padding: 8px; text-align: left; }
        .masking-table th { color: #9ca3af; font-size: 10px; text-transform: uppercase; letter-spacing: .8px; }
        .masking-table td { font-family: 'JetBrains Mono', monospace; color: #d0d8e6; }
        .raw-blur {
            filter: blur(5px);
            transition: filter .2s ease;
            user-select: none;
        }
        .raw-blur:hover { filter: blur(0); }
        .masked-out { color: #00d4aa; font-weight: 700; }
        .score-wrap { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
        .score-circle {
            width: 68px; height: 68px; border-radius: 50%;
            display: grid; place-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700; font-size: 14px;
            border: 2px solid rgba(0,212,170,0.4);
            color: #00d4aa;
            background: radial-gradient(circle at 50% 45%, rgba(0,212,170,0.22), rgba(0,212,170,0.05));
        }
        .score-circle.amber {
            border-color: rgba(255,140,66,0.5);
            color: #ff8c42;
            background: radial-gradient(circle at 50% 45%, rgba(255,140,66,0.25), rgba(255,140,66,0.06));
        }
        .compliance-health {
            margin-top: 10px;
        }
        .health-track {
            margin-top: 6px;
            height: 8px;
            border-radius: 999px;
            background: rgba(255,255,255,0.10);
            overflow: hidden;
        }
        .health-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4aa, #19f0ca);
        }
        .export-row { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
        .export-btn {
            text-decoration: none;
            padding: 9px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .export-btn.csv { background: #00d4aa; color: #07161c; }
        .export-btn.json { background: #ff8c42; color: #120d08; }
        .retention-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 12px;
        }
        .retention-card {
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
            padding: 12px;
        }
        .retention-label { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .8px; }
        .retention-value { margin-top: 6px; font-size: 16px; font-weight: 700; color: #e8edf5; }
        .logs-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            overflow: hidden;
        }
        .logs-table th, .logs-table td {
            padding: 10px 9px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .logs-table th {
            color: #9ca3af;
            background: rgba(255,255,255,0.03);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .8px;
        }
        .logs-table td { color: #cdd5e3; font-family: 'JetBrains Mono', monospace; }
        .terminal-wrap {
            margin-top: 10px;
            border-radius: 12px;
            border: 1px solid rgba(0,212,170,0.28);
            background: #06090d;
            box-shadow: inset 0 0 0 1px rgba(0,212,170,0.08), 0 0 24px rgba(0,212,170,0.12);
            padding: 10px;
        }
        .terminal-head {
            display: flex; justify-content: space-between; align-items: center;
            color: #00d4aa; font-size: 11px; font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }
        #live-terminal {
            max-height: 240px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.45;
            color: #9df6e5;
            white-space: pre-wrap;
        }
        .log-line { display: block; padding: 2px 0; color: #9df6e5; }
        .log-line.flagged { color: #ff6b81; font-weight: 700; }
        .emergency-overlay {
            position: fixed;
            right: 18px;
            bottom: 18px;
            z-index: 80;
            display: block;
            pointer-events: none;
            background: transparent;
            inset: auto;
        }
        .emergency-panel {
            width: min(460px, 92vw);
            border-radius: 16px;
            border: 1px solid rgba(255,76,76,0.55);
            background: rgba(27, 13, 18, 0.9);
            padding: 16px;
            box-shadow: 0 0 0 1px rgba(255,76,76,0.25), 0 0 35px rgba(255,76,76,0.18);
            pointer-events: auto;
        }
        .emergency-close {
            float: right;
            border: 1px solid rgba(255,255,255,0.18);
            background: rgba(255,255,255,0.08);
            color: #f6d3d3;
            border-radius: 999px;
            padding: 2px 9px;
            font-size: 11px;
            cursor: pointer;
        }
        .emergency-title { color: #ff8f8f; font-size: 14px; font-weight: 700; }
        .emergency-sub { color: #f3c1c1; font-size: 12px; margin-top: 6px; font-family: 'JetBrains Mono', monospace; }
        .emergency-btn {
            margin-top: 12px;
            border: 0;
            border-radius: 999px;
            padding: 10px 14px;
            background: #ff4c4c;
            color: #180606;
            font-weight: 800;
            cursor: pointer;
        }
        .alert-card {
            border-radius: 12px; padding: 16px; margin-bottom: 10px;
            border-left-width: 3px; border-left-style: solid;
        }
        .alert-critical { border-left-color: #ff4757; }
        .alert-high { border-left-color: #ff8c42; }
        .alert-medium { border-left-color: #ffd32a; }
        .alert-low { border-left-color: #00d4aa; }
        .alert-header { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 6px; }
        .alert-title { font-size: 15px; font-weight: 600; color: #ecf2ff; }
        .alert-severity {
            font-size: 10px; letter-spacing: 0.9px; text-transform: uppercase;
            border-radius: 999px; padding: 4px 8px; background: rgba(255,255,255,0.08); color: #c2cbe0;
        }
        .alert-desc { font-size: 13px; color: #9ca3af; margin-bottom: 8px; }
        .alert-confidence { font-size: 12px; color: #00d4aa; margin-bottom: 4px; }
        .alert-meta { font-size: 11px; color: #7f8aa2; font-family: 'JetBrains Mono', monospace; }
        .footer {
            margin-top: 20px; padding-top: 14px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: #7f8aa2; font-size: 11px; text-align: center;
        }
        @media (max-width: 980px) {
            .sidebar { position: static; width: 100%; height: auto; }
            .main-content { margin-left: 0; }
            .app-container { display: block; }
            .stats-grid { grid-template-columns: 1fr; }
            .hero-tile, .ops-tile, .signals-tile, .popia-tile, .alerts-tile, .logs-tile { grid-column: 1 / -1; }
        }
    </style>
</head>
<body class="posture-{{ posture.lower() }}">
    <div class="app-container">
        <aside class="sidebar">
            <div class="logo">
                <div class="logo-badge" aria-hidden="true">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.2"></rect>
                        <rect x="5.2" y="4.4" width="1.1" height="2.3" rx="0.3" fill="currentColor"></rect>
                        <rect x="7.7" y="4.4" width="1.1" height="2.3" rx="0.3" fill="currentColor"></rect>
                    </svg>
                </div>
                <div class="logo-text">Proactive Sentinel</div>
            </div>
            <a href="#dashboard" class="nav-item active">Dashboard</a>
            <a href="#architecture" class="nav-item">Architecture</a>
            <a href="#popia" class="nav-item">POPIA</a>
            <a href="#logs" class="nav-item">Logs</a>
        </aside>

        <main class="main-content">
            <div class="top-bar">
                <div class="clock-stack">
                    <div id="clock-sast" class="clock-line">[SAST] {{ current_sast }}</div>
                    <div id="clock-utc" class="clock-line">[UTC] {{ current_time }} UTC</div>
                    <div class="clock-sub">SENTINEL_GUARD: ACTIVE_SCANNING</div>
                </div>
                <div class="user-info">
                    <span id="live-status" class="live-status"><span class="live-dot"></span><span id="live-status-text">LIVE</span></span>
                    <span class="popia-badge">POPIA §18</span>
                    <span class="user-email">{{ user.email }}</span>
                    <a href="/logout" class="logout-btn">SOC Console</a>
                </div>
            </div>

            <section class="bento-grid">
                <article id="dashboard" class="threat-map hero-tile hover-expand">
                    <div class="threat-map-header">
                        <span class="threat-map-title">Threat Posture</span>
                        <span id="threat-posture-label" class="elevated-badge">{{ posture }}</span>
                    </div>
                    <div class="company-name">Zororo Phumulani Funeral Logistics SOC</div>
                    <div class="company-desc">Cross-channel security posture for Claims, WhatsApp, Member Portals, Lead Management, Finance and Repatriation.</div>
                    <div class="gov-ticker">
                        <div id="ticker-fraud" class="ticker-item {{ governance_ticker.fraud }}">$FRAUD {{ governance_metrics.fraud_events }}</div>
                        <div id="ticker-popia" class="ticker-item {{ governance_ticker.popia }}">$POPIA {{ governance_metrics.unmasked_pii }}</div>
                        <div id="ticker-kyc" class="ticker-item {{ governance_ticker.kyc }}">$KYC {{ governance_metrics.kyc_verified }}%</div>
                        <div id="ticker-hack" class="ticker-item {{ governance_ticker.hack }}">$HACK {{ governance_metrics.hack_events }}</div>
                    </div>
                    <div class="market-wrap">
                        <div id="threat-market-chart"></div>
                    </div>
                </article>

                <article id="architecture" class="stat-card ops-tile hover-expand">
                    <h3>Service Mesh</h3>
                    <div class="status-badge">Docker Stack + Cloud Heartbeat</div>
                    <div class="health-list" style="margin-top:10px">
                        {% for service, state in health_services.items() %}
                        <div class="health-pill {{ 'ok' if state == 'healthy' else 'critical' if state == 'critical' else 'bad' }}">{{ service }}: {{ state }}</div>
                        {% endfor %}
                    </div>
                    <div class="arch-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));margin-top:8px">
                        {% for item in architecture_items %}
                        <article class="arch-item">
                            <div class="arch-name">{{ item.name }}</div>
                            <div class="arch-value">{{ item.value }}</div>
                        </article>
                        {% endfor %}
                    </div>
                </article>

                <article class="stat-card signals-tile hover-expand">
                    <h3>Department Robots (RAG)</h3>
                    <div class="pulse-grid" id="pulse-grid-live">
                        {% for p in pulse_points %}
                        <div id="robot-{{ p.key }}" class="pulse-item {{ 'amber' if p.state == 'AMBER' else 'red' if p.state == 'RED' else '' }}">
                            <div class="robot-dot {{ 'robot-green' if p.state == 'GREEN' else 'robot-amber' if p.state == 'AMBER' else 'robot-red' }}"></div>
                            <div class="pulse-label">{{ p.name }}</div>
                            <div class="pulse-value">{{ p.state }} | {{ p.latency_ms }}ms</div>
                            <div class="commentary-box">SIGNAL: {{ p.name }} | REASON: {{ p.reason }} | RISK: {{ p.risk }}</div>
                        </div>
                        {% endfor %}
                    </div>
                </article>

                <article id="popia" class="stat-card popia-tile hover-expand">
                    <div class="section-title">POPIA Compliance</div>
                    <div class="score-wrap">
                        <div class="status-badge">Transparency Layer</div>
                        <div class="score-circle {{ 'amber' if compliance_score < 98 else '' }}">{{ compliance_score }}%</div>
                    </div>
                    <div class="retention-grid">
                        <article class="retention-card">
                            <div class="retention-label">Retention Days</div>
                            <div class="retention-value">{{ retention.retention_days }}</div>
                        </article>
                        <article class="retention-card">
                            <div class="retention-label">Archive Candidates</div>
                            <div class="retention-value">{{ retention.old_logs_count }}</div>
                        </article>
                        <article class="retention-card">
                            <div class="retention-label">Next Archive Date</div>
                            <div class="retention-value" style="font-size:12px">{{ retention.next_archive_date }}</div>
                        </article>
                    </div>
                    <div class="status-badge">{{ retention.retention_policy }}</div>
                    <table class="masking-table">
                        <thead>
                            <tr><th>Input Type</th><th>Raw String (Hidden)</th><th>VRL Output</th></tr>
                        </thead>
                        <tbody>
                            {% for row in masking_preview %}
                            <tr>
                                <td>{{ row.kind }}</td>
                                <td><span class="raw-blur">{{ row.original }}</span></td>
                                <td><span class="masked-out">{{ row.masked }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    <div class="compliance-health">
                        <div class="retention-label">Compliance Health</div>
                        <div class="health-track">
                            <div class="health-fill" style="width: {{ compliance_health }}%"></div>
                        </div>
                    </div>
                </article>

                <article class="alerts-section alerts-tile">
                    <h2>Recent Alerts</h2>
                    {% for alert in alerts %}
                    <article class="alert-card alert-{{ alert.severity }} hover-expand">
                        <div class="alert-header">
                            <span class="alert-title">{{ alert.title }}</span>
                            <span class="alert-severity">{{ alert.severity.upper() }}</span>
                        </div>
                        <div class="alert-desc">{{ alert.description }}</div>
                        <div class="alert-confidence">AI Confidence: {{ alert.confidence }}%</div>
                        <div class="alert-meta">{{ alert.source }} | {{ alert.created_at }}</div>
                    </article>
                    {% else %}
                    <article class="alert-card">
                        <div class="alert-desc">No alerts found.</div>
                    </article>
                    {% endfor %}
                </article>

                <article id="logs" class="stat-card logs-tile hover-expand">
                    <div class="section-title">Live SOC Logs</div>
                    <div class="export-row" style="justify-content:flex-end">
                        <a class="export-btn csv" href="/exports/security-telemetry.csv">Export Security Telemetry (CSV)</a>
                        <a class="export-btn json" href="/exports/masked-identity-logs.json">Export Masked Identity Logs (JSON)</a>
                        <a class="export-btn csv" href="/exports/daily-governance-report.csv">Daily Governance Report (CSV)</a>
                    </div>
                    <div class="terminal-wrap">
                        <div class="terminal-head">
                            <span>tail -f proactive_sentinel/audit.log</span>
                            <span id="terminal-state">LIVE</span>
                        </div>
                        <div id="live-terminal">
                            {% for line in terminal_lines %}
                            <span class="log-line {{ 'flagged' if line.flagged else '' }}">{{ line.text }}</span>
                            {% endfor %}
                        </div>
                    </div>
                </article>
            </section>
            {% if emergency_active %}
            <div class="emergency-overlay" id="emergency-overlay">
                <div class="emergency-panel" id="emergency-panel">
                    <button class="emergency-close" type="button" onclick="dismissEmergency()">Dismiss</button>
                    <div class="emergency-title">Emergency Protocol Active</div>
                    <div class="emergency-sub">Context: {{ emergency_context }}</div>
                    {% if emergency_identity %}
                    <div class="emergency-sub">POPIA Identity Breach: {{ emergency_identity }}</div>
                    {% endif %}
                    <form method="post" action="/emergency-alert">
                        <input type="hidden" name="context" value="{{ emergency_context }}">
                        <input type="hidden" name="identity" value="{{ emergency_identity }}">
                        <button class="emergency-btn" type="submit">SEND EMERGENCY ALERT</button>
                    </form>
                </div>
            </div>
            {% endif %}

            <div class="footer">
                POPIA Section 18 | {{ current_time }} UTC | SOC Console
            </div>
        </main>
    </div>
<script>
async function refreshLiveLogs() {
    try {
        const response = await fetch('/live/logs');
        if (!response.ok) return;
        const data = await response.json();
        const terminal = document.getElementById('live-terminal');
        const state = document.getElementById('terminal-state');
        if (!terminal || !state) return;
        terminal.innerHTML = '';
        (data.lines || []).forEach((line) => {
            const span = document.createElement('span');
            span.className = 'log-line' + (line.flagged ? ' flagged' : '');
            span.textContent = line.text;
            terminal.appendChild(span);
        });
        terminal.scrollTop = terminal.scrollHeight;
        state.textContent = data.pre_incident ? 'PRE-INCIDENT' : 'LIVE';
        document.body.classList.remove('posture-clean', 'posture-elevated', 'posture-critical');
        const posture = (data.posture || 'CLEAN').toLowerCase();
        document.body.classList.add('posture-' + posture);
        const postureLabel = document.getElementById('threat-posture-label');
        if (postureLabel) postureLabel.textContent = (data.posture || 'CLEAN').toUpperCase();
        const pulseGrid = document.getElementById('pulse-grid-live');
        if (pulseGrid && Array.isArray(data.pulse_points)) {
            pulseGrid.innerHTML = '';
            data.pulse_points.forEach((p) => {
                const tile = document.createElement('div');
                tile.id = `robot-${p.key || 'robot'}`;
                tile.className = 'pulse-item ' + (p.state === 'AMBER' ? 'amber' : p.state === 'RED' ? 'red' : '');
                const dotClass = p.state === 'RED' ? 'robot-red' : p.state === 'AMBER' ? 'robot-amber' : 'robot-green';
                tile.innerHTML = `
                    <div class="robot-dot ${dotClass}"></div>
                    <div class="pulse-label">${p.name}</div>
                    <div class="pulse-value">${p.state} | ${p.latency_ms}ms</div>
                    <div class="commentary-box">SIGNAL: ${p.name} | REASON: ${p.reason} | RISK: ${p.risk}</div>
                `;
                pulseGrid.appendChild(tile);
            });
        }
        const setTicker = (id, klass, text) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.className = `ticker-item ${klass}`;
            el.textContent = text;
        };
        if (data.governance_metrics && data.governance_ticker) {
            setTicker('ticker-fraud', data.governance_ticker.fraud, `$FRAUD ${data.governance_metrics.fraud_events}`);
            setTicker('ticker-popia', data.governance_ticker.popia, `$POPIA ${data.governance_metrics.unmasked_pii}`);
            setTicker('ticker-kyc', data.governance_ticker.kyc, `$KYC ${data.governance_metrics.kyc_verified}%`);
            setTicker('ticker-hack', data.governance_ticker.hack, `$HACK ${data.governance_metrics.hack_events}`);
        }
        if (data.governance_chart && chart) {
            chart.updateSeries([
                { name: 'Risk Score', type: 'candlestick', data: data.governance_chart.candles || [] },
                { name: 'Volume', type: 'bar', data: data.governance_chart.volume || [] }
            ], true);
        }
        const liveStatus = document.getElementById('live-status');
        const liveStatusText = document.getElementById('live-status-text');
        if (liveStatus && liveStatusText) {
            liveStatus.classList.remove('offline');
            liveStatusText.textContent = 'LIVE';
        }
    } catch (err) {
        const liveStatus = document.getElementById('live-status');
        const liveStatusText = document.getElementById('live-status-text');
        if (liveStatus && liveStatusText) {
            liveStatus.classList.add('offline');
            liveStatusText.textContent = 'DISCONNECTED';
        }
    }
}
function dismissEmergency() {
    const overlay = document.getElementById('emergency-overlay');
    if (overlay) overlay.style.display = 'none';
    localStorage.setItem('ps_emergency_dismissed', '1');
}
(() => {
    const dismissed = localStorage.getItem('ps_emergency_dismissed');
    const overlay = document.getElementById('emergency-overlay');
    if (dismissed === '1' && overlay) overlay.style.display = 'none';
})();
setInterval(refreshLiveLogs, 5000);

const marketSeries = {{ governance_chart | safe }};
const marketOptions = {
    chart: { type: 'candlestick', height: 250, background: 'transparent', toolbar: { show: false } },
    series: [
        { name: 'Risk Score', type: 'candlestick', data: marketSeries.candles || [] },
        { name: 'Volume', type: 'bar', data: marketSeries.volume || [] }
    ],
    plotOptions: {
        candlestick: {
            colors: { upward: '#00d4aa', downward: '#ff4757' },
            wick: { useFillColor: false }
        },
        bar: { columnWidth: '55%' }
    },
    colors: ['#00d4aa', '#ff4c4c'],
    yaxis: [{ max: 100, min: 0 }, { opposite: true }],
    xaxis: { type: 'datetime', labels: { datetimeUTC: false } },
    stroke: { width: [1, 0] },
    theme: { mode: 'dark' },
    legend: { labels: { colors: '#9ca3af' } },
    grid: { borderColor: 'rgba(255,255,255,0.08)' }
};
const chart = new ApexCharts(document.querySelector('#threat-market-chart'), marketOptions);
chart.render();

function pad2(v) { return String(v).padStart(2, '0'); }
function formatDDMMYYYY(date) {
    return `${pad2(date.getDate())}/${pad2(date.getMonth() + 1)}/${date.getFullYear()}`;
}
function updateDualClock() {
    const now = new Date();
    const utcHours = now.getUTCHours();
    const utcMinutes = now.getUTCMinutes();
    const utcSeconds = now.getUTCSeconds();
    const utcLabel = `${formatDDMMYYYY(now)} ${pad2(utcHours)}:${pad2(utcMinutes)}:${pad2(utcSeconds)}`;

    // SAST/Harare corridor is UTC+2 (no DST in both zones)
    const sastDate = new Date(now.getTime() + (2 * 60 * 60 * 1000));
    const sastHours = sastDate.getUTCHours();
    const sastMinutes = sastDate.getUTCMinutes();
    const sastSeconds = sastDate.getUTCSeconds();
    const sastLabel = `${formatDDMMYYYY(sastDate)} ${pad2(sastHours)}:${pad2(sastMinutes)}:${pad2(sastSeconds)}`;

    const sastEl = document.getElementById('clock-sast');
    const utcEl = document.getElementById('clock-utc');
    if (sastEl) sastEl.textContent = `[SAST] ${sastLabel}`;
    if (utcEl) utcEl.textContent = `[UTC] ${utcLabel}`;
}
setInterval(updateDualClock, 1000);
updateDualClock();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    if "access_token" not in session:
        return redirect(url_for("login_page"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET"])
def login_page():
    return render_template_string(LOGIN_TEMPLATE)


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            session["access_token"] = data["access_token"]
            session["user"] = data.get("user", {"email": email})
            return redirect(url_for("dashboard"))
        import logging
        logging.error(f"Login failed: status={response.status_code} body={response.text[:200]}")
        flash(f"Login failed ({response.status_code}): {response.text[:100]}")
    except Exception as e:
        import logging
        logging.error(f"Login exception: {e}")
        flash(f"Connection error: {e}")

    return redirect(url_for("login_page"))


@app.route("/dashboard")
def dashboard():
    if "access_token" not in session:
        return redirect(url_for("login_page"))

    def _api_get(path, headers=None, timeout=5):
        try:
            response = requests.get(path, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except Exception:
            return None
        return None

    try:
        headers = {"Authorization": f'Bearer {session["access_token"]}'}
        alerts_payload = _api_get(f"{API_BASE_URL}/alerts", headers=headers) or {}
        alerts = alerts_payload.get("alerts", [])
        for alert in alerts:
            alert["created_at"] = alert.get("created_at", "")[:19] if alert.get("created_at") else "Just now"
            alert["confidence"] = alert.get("confidence", 85)

        # Health endpoint may exist at either /api/health or /health
        health_payload = _api_get(HEALTH_URL) or _api_get(f"{API_BASE_URL}/health") or _api_get(
            API_BASE_URL.replace("/api", "/health")
        ) or {}
        health_services = health_payload.get("services", {}) or {
            "api": "unknown",
            "database": "unknown",
            "redis": "unknown",
        }
        # Access layer: Docker stack + cloud heartbeat
        health_services = {
            "postgres": health_services.get("database", health_services.get("postgres", "unknown")),
            "redis": health_services.get("redis", "unknown"),
            "api": health_services.get("api", "healthy"),
            "aws-t3-micro": "healthy",
        }

        retention = _api_get(f"{API_BASE_URL}/audit/retention", headers=headers) or {
            "retention_days": 365,
            "old_logs_count": 0,
            "next_archive_date": "n/a",
            "retention_policy": "1 year hot storage, 7 years cold storage",
        }

        logs_payload = _api_get(f"{API_BASE_URL}/audit/logs?per_page=8", headers=headers) or {}
        audit_logs = logs_payload.get("logs", [])
        for row in audit_logs:
            row["timestamp"] = (row.get("timestamp") or "")[:19] or "n/a"
            row["resource_type"] = row.get("resource_type") or "n/a"
            row["resource_id"] = row.get("resource_id") or "n/a"
            row["source_ip"] = row.get("source_ip") or "n/a"

        architecture_items = [
            {"name": "Collector", "value": "Wazuh + GuardDuty"},
            {"name": "Correlation", "value": "Python + Redis"},
            {"name": "Storage", "value": "PostgreSQL + Audit"},
            {"name": "Response", "value": "Risk-Based Actions"},
        ]
        critical_count = 0
        high_count = 0
        medium_count = 0
        suspicious_events = 0
        for alert in alerts:
            sev = (alert.get("severity") or "").lower()
            if sev == "critical":
                critical_count += 1
            elif sev == "high":
                high_count += 1
            elif sev == "medium":
                medium_count += 1
            txt = f"{alert.get('title','')} {alert.get('description','')}".lower()
            if "suspicious" in txt:
                suspicious_events += 1
        for row in audit_logs:
            txt = f"{row.get('action','')} {row.get('resource_type','')} {row.get('resource_id','')}".lower()
            if "suspicious" in txt:
                suspicious_events += 1

        risk_score = min(100, (critical_count * 35) + (high_count * 15) + (medium_count * 8) + (suspicious_events * 10))
        if risk_score < 50 and critical_count == 0:
            posture = "CLEAN"
            robot_state = "GREEN"
        elif (50 <= risk_score <= 75) or suspicious_events > 0:
            posture = "ELEVATED"
            robot_state = "AMBER"
        else:
            posture = "CRITICAL"
            robot_state = "RED"

        pulse_points = [
            {"key": "claims", "name": "Claims", "latency_ms": 11, "state": "AMBER" if suspicious_events else "GREEN", "reason": "Suspicious claims pattern" if suspicious_events else "Claim flow normal", "risk": "LOW" if suspicious_events else "SAFE"},
            {"key": "leads", "name": "Leads", "latency_ms": 8, "state": "GREEN", "reason": "Lead flow normal", "risk": "SAFE"},
            {"key": "finance", "name": "Finance", "latency_ms": 10, "state": "AMBER" if suspicious_events else "GREEN", "reason": "Suspicious payout pattern" if suspicious_events else "Premium flow normal", "risk": "LOW" if suspicious_events else "SAFE"},
            {"key": "transport", "name": "Transport", "latency_ms": 16 if robot_state != "RED" else 33, "state": "RED" if robot_state == "RED" else "AMBER" if robot_state == "AMBER" else "GREEN", "reason": "Beitbridge Border Delay detected" if robot_state == "RED" else "Route timings stable", "risk": "HIGH" if robot_state == "RED" else "MEDIUM" if robot_state == "AMBER" else "SAFE"},
            {"key": "hr", "name": "HR", "latency_ms": 7, "state": "GREEN", "reason": "No unauthorized salary access", "risk": "SAFE"},
            {"key": "cyber", "name": "Cyber", "latency_ms": 12, "state": "RED" if critical_count > 0 else "AMBER" if suspicious_events else "GREEN", "reason": "Critical threat confirmed" if critical_count > 0 else "Suspicious event activity" if suspicious_events else "Guard Duty stable", "risk": "HIGH" if critical_count > 0 else "MEDIUM" if suspicious_events else "SAFE"},
        ]

        def _mask_identity(value):
            raw = str(value or "")
            if len(raw) < 6:
                return "******"
            return f"{raw[:2]}******{raw[-2:]}"

        pii_regexes = [
            re.compile(r"\b\d{13}\b"),  # SA ID style
            re.compile(r"\b\d{2}-\d{6}\s?[A-Z]\d{2}\b"),  # Zim ID style
            re.compile(r"\b[A-Z]{1,2}\d{6,8}\b"),  # Passport style
        ]
        unmasked_hits = 0
        for alert in alerts:
            text_blob = " ".join(
                str(alert.get(k, "")) for k in ("title", "description", "source", "raw", "message")
            )
            if any(rx.search(text_blob) for rx in pii_regexes):
                unmasked_hits += 1

        masking_preview = [
            {"kind": "SA ID", "original": "9001015800087", "masked": _mask_identity("9001015800087")},
            {"kind": "Zim ID", "original": "12-345678 Z80", "masked": _mask_identity("12-345678 Z80")},
            {"kind": "Passport", "original": "ZN1234567", "masked": _mask_identity("ZN1234567")},
        ]
        compliance_score = max(70, 98 - (unmasked_hits * 4))
        compliance_health = 100 if compliance_score >= 98 else 82

        terminal_lines, pre_incident, posture = build_terminal_lines(audit_logs, posture)

        governance_metrics = {
            "fraud_events": 0,
            "unmasked_pii": unmasked_hits,
            "kyc_verified": 100 if compliance_score >= 98 else 93,
            "hack_events": 0,
        }
        for row in audit_logs:
            action = str(row.get("action", "")).lower()
            text = f"{action} {row.get('resource_type','')} {row.get('resource_id','')}".lower()
            if "duplicate" in text or "multiple payouts" in text:
                governance_metrics["fraud_events"] += 1
            if "sql" in text or "brute" in text or "failed_login" in text:
                governance_metrics["hack_events"] += 1

        def _ticker_class(value, warn_threshold=1):
            if value == 0:
                return "safe"
            if value <= warn_threshold:
                return "warn"
            return "risk"

        governance_ticker = {
            "fraud": _ticker_class(governance_metrics["fraud_events"], 2),
            "popia": _ticker_class(governance_metrics["unmasked_pii"], 0),
            "kyc": "safe" if governance_metrics["kyc_verified"] >= 98 else "warn",
            "hack": _ticker_class(governance_metrics["hack_events"], 2),
        }

        # Candlestick + volume risk market chart data
        candles = []
        volume = []
        base = max(20, min(95, risk_score))
        bar_color = "#00d4aa" if posture == "CLEAN" else "#ffb347" if posture == "ELEVATED" else "#ff4c4c"
        for i in range(10):
            ts = int((datetime.utcnow() - timedelta(minutes=(9 - i) * 5)).timestamp() * 1000)
            open_v = max(0, min(100, base - 2))
            close_v = max(0, min(100, base + (2 if posture == "CLEAN" else -1 if posture == "ELEVATED" else -4)))
            high_v = max(open_v, close_v) + 3
            low_v = min(open_v, close_v) - 3
            candles.append({"x": ts, "y": [open_v, high_v, low_v, close_v]})
            volume.append({"x": ts, "y": max(5, len(audit_logs) + i + (6 if posture == "CRITICAL" else 2 if posture == "ELEVATED" else 0)), "fillColor": bar_color})
        governance_chart = json.dumps({"candles": candles, "volume": volume})
        emergency_active = posture == "CRITICAL"
        emergency_blocking = False
        emergency_context = "Emergency state raised by Transport/Cyber guardrails."
        emergency_identity = "ZN******67" if unmasked_hits > 0 else ""
    except Exception:
        alerts = []
        health_services = {"postgres": "unknown", "redis": "unknown", "api": "unknown", "aws-t3-micro": "unknown"}
        retention = {
            "retention_days": 365,
            "old_logs_count": 0,
            "next_archive_date": "n/a",
            "retention_policy": "1 year hot storage, 7 years cold storage",
        }
        audit_logs = []
        architecture_items = [
            {"name": "Collector", "value": "Wazuh + GuardDuty"},
            {"name": "Correlation", "value": "Python + Redis"},
            {"name": "Storage", "value": "PostgreSQL + Audit"},
            {"name": "Response", "value": "Risk-Based Actions"},
        ]
        risk_score = 0
        pulse_points = [
            {"key": "claims", "name": "Claims", "latency_ms": 0, "state": "GREEN", "reason": "No events", "risk": "SAFE"},
            {"key": "leads", "name": "Leads", "latency_ms": 0, "state": "GREEN", "reason": "No events", "risk": "SAFE"},
            {"key": "finance", "name": "Finance", "latency_ms": 0, "state": "GREEN", "reason": "No events", "risk": "SAFE"},
            {"key": "transport", "name": "Transport", "latency_ms": 0, "state": "GREEN", "reason": "No events", "risk": "SAFE"},
            {"key": "hr", "name": "HR", "latency_ms": 0, "state": "GREEN", "reason": "No events", "risk": "SAFE"},
            {"key": "cyber", "name": "Cyber", "latency_ms": 0, "state": "GREEN", "reason": "No events", "risk": "SAFE"},
        ]
        posture = "CLEAN"
        masking_preview = [
            {"kind": "SA ID", "original": "9001015800087", "masked": "90******87"},
            {"kind": "Zim ID", "original": "12-345678 Z80", "masked": "12******80"},
            {"kind": "Passport", "original": "ZN1234567", "masked": "ZN******67"},
        ]
        compliance_score = 98
        compliance_health = 100
        terminal_lines, pre_incident, posture = build_terminal_lines(audit_logs, posture)
        governance_metrics = {"fraud_events": 0, "unmasked_pii": 0, "kyc_verified": 100, "hack_events": 0}
        governance_ticker = {"fraud": "safe", "popia": "safe", "kyc": "safe", "hack": "safe"}
        governance_chart = json.dumps({"candles": [], "volume": []})
        emergency_active = False
        emergency_blocking = False
        emergency_context = "No emergency"
        emergency_identity = ""

    return render_template_string(
        DASHBOARD_TEMPLATE,
        user=session.get("user", {}),
        alerts=alerts,
        health_services=health_services,
        retention=retention,
        audit_logs=audit_logs,
        architecture_items=architecture_items,
        pulse_points=pulse_points,
        posture=posture,
        masking_preview=masking_preview,
        compliance_score=compliance_score,
        compliance_health=compliance_health,
        terminal_lines=terminal_lines,
        pre_incident=pre_incident,
        governance_metrics=governance_metrics,
        governance_ticker=governance_ticker,
        governance_chart=governance_chart,
        risk_score=risk_score,
        emergency_active=emergency_active,
        emergency_blocking=emergency_blocking,
        emergency_context=emergency_context,
        emergency_identity=emergency_identity,
        current_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        current_sast=(datetime.utcnow() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M:%S"),
    )


def build_terminal_lines(audit_logs, posture):
    now = datetime.utcnow()
    failed_login_recent = 0
    repatriation_timeout = False
    lines = []
    for row in audit_logs[-10:]:
        ts_raw = row.get("timestamp") or ""
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", ""))
        except Exception:
            ts = now
        action = str(row.get("action") or "EVENT").upper().replace(" ", "_")
        source = str(row.get("resource_type") or "SYSTEM").upper()
        status = str(row.get("new_value") or row.get("resource_id") or row.get("source_ip") or "OK")
        status_text = str(status).upper()
        flagged = False

        if "FAILED" in action and "LOGIN" in action and (now - ts) <= timedelta(seconds=60):
            failed_login_recent += 1
        # Live log sieve for fraud + governance indicators
        if (
            "DUPLICATE" in action
            or "SQL" in action
            or "INJECTION" in action
            or "UNAUTHORIZED_SALARY_DATA_ACCESS" in action
            or "MULTIPLE_PAYOUTS_TO_SINGLE_ACCOUNT" in action
            or "REPATRIATION_TRANSPORT_DELAYS" in action
            or "BEITBRIDGE_BORDER_DELAY" in action
        ):
            flagged = True
        if ("REPATRIATION" in source or "REPATRIATION" in action) and (
            "TIMEOUT" in action or "TIMEOUT" in status_text
        ) and (now - ts) <= timedelta(seconds=60):
            repatriation_timeout = True

        line = f"[{ts.strftime('%H:%M:%S')}] [{source}] {action} -> {status}"
        lines.append({"text": line, "flagged": flagged})

    pre_incident = failed_login_recent >= 3 or repatriation_timeout
    if pre_incident:
        posture = "CRITICAL"
        for line in lines:
            t = line["text"].upper()
            if ("FAILED_LOGIN" in t) or ("REPATRIATION" in t and "TIMEOUT" in t):
                line["flagged"] = True
    return lines, pre_incident, posture


@app.route("/live/logs")
def live_logs():
    if "access_token" not in session:
        return Response(json.dumps({"lines": [], "posture": "CLEAN", "pre_incident": False}), mimetype="application/json")
    headers = {"Authorization": f'Bearer {session["access_token"]}'}
    audit_logs = []
    alerts = []
    posture = "CLEAN"
    try:
        response = requests.get(f"{API_BASE_URL}/audit/logs?per_page=10", headers=headers, timeout=5)
        if response.status_code == 200:
            audit_logs = response.json().get("logs", [])
        alert_response = requests.get(f"{API_BASE_URL}/alerts", headers=headers, timeout=5)
        if alert_response.status_code == 200:
            alerts = alert_response.json().get("alerts", [])
            posture = "ELEVATED" if any((a.get("severity") or "").lower() in {"high", "medium"} for a in alerts) else "CLEAN"
            if any((a.get("severity") or "").lower() == "critical" for a in alerts):
                posture = "CRITICAL"
    except Exception:
        pass
    lines, pre_incident, posture = build_terminal_lines(audit_logs, posture)
    # lightweight live robot/ticker/chart projection
    fraud_events = 0
    hack_events = 0
    unmasked_pii = 0
    for row in audit_logs:
        t = f"{row.get('action','')} {row.get('resource_type','')} {row.get('resource_id','')}".lower()
        if "duplicate" in t or "multiple payouts" in t:
            fraud_events += 1
        if "brute" in t or "sql" in t or "injection" in t or "failed_login" in t:
            hack_events += 1
    for alert in alerts:
        blob = " ".join(str(alert.get(k, "")) for k in ("title", "description", "message"))
        if re.search(r"\b\d{13}\b", blob) or re.search(r"\b[A-Z]{1,2}\d{6,8}\b", blob):
            unmasked_pii += 1
    critical_count = sum(1 for a in alerts if (a.get("severity") or "").lower() == "critical")
    suspicious_events = 0
    for a in alerts:
        if "suspicious" in f"{a.get('title','')} {a.get('description','')}".lower():
            suspicious_events += 1
    governance_metrics = {
        "fraud_events": fraud_events,
        "unmasked_pii": unmasked_pii,
        "kyc_verified": 100 if unmasked_pii == 0 else 93,
        "hack_events": hack_events,
    }
    risk_score = min(100, (critical_count * 35) + (hack_events * 10) + (fraud_events * 10) + (suspicious_events * 10))
    if risk_score < 50 and critical_count == 0:
        posture = "CLEAN"
        state = "GREEN"
    elif (50 <= risk_score <= 75) or suspicious_events > 0:
        posture = "ELEVATED"
        state = "AMBER"
    else:
        posture = "CRITICAL"
        state = "RED"
    governance_ticker = {
        "fraud": "safe" if fraud_events == 0 else "warn" if fraud_events <= 2 else "risk",
        "popia": "safe" if unmasked_pii == 0 else "risk",
        "kyc": "safe" if governance_metrics["kyc_verified"] >= 98 else "warn",
        "hack": "safe" if hack_events == 0 else "warn" if hack_events <= 2 else "risk",
    }
    pulse_points = [
        {"key": "claims", "name": "Claims", "latency_ms": 12, "state": "AMBER" if suspicious_events else "GREEN", "reason": "Suspicious claims pattern" if suspicious_events else "No claim anomalies", "risk": "LOW" if suspicious_events else "SAFE"},
        {"key": "leads", "name": "Leads", "latency_ms": 8, "state": "GREEN", "reason": "Lead flow normal", "risk": "SAFE"},
        {"key": "finance", "name": "Finance", "latency_ms": 10, "state": "AMBER" if suspicious_events else "GREEN", "reason": "Multiple payouts to 1 Bank Acc" if suspicious_events else "Premium flow normal", "risk": "LOW" if suspicious_events else "SAFE"},
        {"key": "transport", "name": "Transport", "latency_ms": 33 if state == "RED" else 18 if state == "AMBER" else 12, "state": "RED" if state == "RED" else "AMBER" if state == "AMBER" else "GREEN", "reason": "Beitbridge Border Delay detected" if state == "RED" else "Route timings normal", "risk": "HIGH" if state == "RED" else "MEDIUM" if state == "AMBER" else "SAFE"},
        {"key": "hr", "name": "HR", "latency_ms": 7, "state": "GREEN", "reason": "No unauthorized salary access", "risk": "SAFE"},
        {"key": "cyber", "name": "Cyber", "latency_ms": 11, "state": "RED" if critical_count > 0 else "AMBER" if suspicious_events else "GREEN", "reason": "Critical threat confirmed" if critical_count > 0 else "Suspicious activity" if suspicious_events else "Guard Duty stable", "risk": "HIGH" if critical_count > 0 else "MEDIUM" if suspicious_events else "SAFE"},
    ]
    # chart refresh dataset
    candles = []
    volume = []
    base = max(20, min(95, risk_score))
    bar_color = "#00d4aa" if state == "GREEN" else "#ffb347" if state == "AMBER" else "#ff4c4c"
    for i in range(10):
        ts = int((datetime.utcnow() - timedelta(minutes=(9 - i) * 5)).timestamp() * 1000)
        open_v = max(0, min(100, base - 2))
        close_v = max(0, min(100, base + (2 if state == "GREEN" else -1 if state == "AMBER" else -4)))
        high_v = max(open_v, close_v) + 4
        low_v = min(open_v, close_v) - 4
        candles.append({"x": ts, "y": [open_v, high_v, low_v, close_v]})
        volume.append({"x": ts, "y": max(5, len(audit_logs) + i + (6 if state == "RED" else 2 if state == "AMBER" else 0)), "fillColor": bar_color})
    governance_chart = {"candles": candles, "volume": volume}
    return Response(
        json.dumps({
            "lines": lines,
            "posture": posture,
            "pre_incident": pre_incident,
            "pulse_points": pulse_points,
            "governance_metrics": governance_metrics,
            "governance_ticker": governance_ticker,
            "governance_chart": governance_chart,
            "risk_score": risk_score,
        }),
        mimetype="application/json",
    )


@app.route("/exports/security-telemetry.csv")
def export_security_telemetry_csv():
    if "access_token" not in session:
        return redirect(url_for("login_page"))
    headers = {"Authorization": f'Bearer {session["access_token"]}'}
    alerts = []
    try:
        response = requests.get(f"{API_BASE_URL}/alerts", headers=headers, timeout=5)
        if response.status_code == 200:
            alerts = response.json().get("alerts", [])
    except Exception:
        alerts = []
    rows = ["timestamp,severity,title,source,confidence"]
    for a in alerts:
        rows.append(
            f"{(a.get('created_at') or '')[:19]},{a.get('severity','')},{str(a.get('title','')).replace(',', ' ')},{a.get('source','')},{a.get('confidence', '')}"
        )
    return Response(
        "\n".join(rows),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=security_telemetry.csv"},
    )


@app.route("/exports/masked-identity-logs.json")
def export_masked_identity_logs_json():
    if "access_token" not in session:
        return redirect(url_for("login_page"))
    sample = [
        {"identity_type": "SA ID", "masked": "90******87"},
        {"identity_type": "Zim ID", "masked": "12******80"},
        {"identity_type": "Passport", "masked": "ZN******67"},
    ]
    return Response(
        json.dumps({"exported_at": datetime.utcnow().isoformat(), "records": sample}),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=masked_identity_logs.json"},
    )


@app.route("/exports/daily-governance-report.csv")
def export_daily_governance_report_csv():
    if "access_token" not in session:
        return redirect(url_for("login_page"))
    headers = {"Authorization": f'Bearer {session["access_token"]}'}
    alerts = []
    audit_logs = []
    try:
        a_res = requests.get(f"{API_BASE_URL}/alerts", headers=headers, timeout=5)
        if a_res.status_code == 200:
            alerts = a_res.json().get("alerts", [])
        l_res = requests.get(f"{API_BASE_URL}/audit/logs?per_page=200", headers=headers, timeout=5)
        if l_res.status_code == 200:
            audit_logs = l_res.json().get("logs", [])
    except Exception:
        pass

    fraud = 0
    hack = 0
    logistics_delay = 0
    hr_guard = 0
    for row in audit_logs:
        t = f"{row.get('action','')} {row.get('resource_type','')} {row.get('resource_id','')}".lower()
        if "duplicate" in t or "multiple payouts" in t:
            fraud += 1
        if "brute" in t or "sql" in t or "injection" in t or "failed_login" in t:
            hack += 1
        if "repatriation" in t and ("delay" in t or "timeout" in t):
            logistics_delay += 1
        if "salary" in t and "unauthorized" in t:
            hr_guard += 1
    critical_alerts = sum(1 for a in alerts if str(a.get("severity", "")).lower() == "critical")
    rows = [
        "report_date,fraud_indicators,hack_indicators,hr_guard_incidents,logistics_delays,critical_alerts",
        f"{datetime.utcnow().date().isoformat()},{fraud},{hack},{hr_guard},{logistics_delay},{critical_alerts}",
    ]
    for incident in EMERGENCY_INCIDENTS[-10:]:
        rows.append(
            f"{incident.get('date')},EMERGENCY_ALERT,1,0,0,{incident.get('context','')}"
        )
    return Response(
        "\n".join(rows),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=daily_governance_report.csv"},
    )


@app.route("/emergency-alert", methods=["POST"])
def emergency_alert():
    if "access_token" not in session:
        return redirect(url_for("login_page"))
    context = request.form.get("context", "Emergency protocol triggered")
    identity = request.form.get("identity", "")
    EMERGENCY_INCIDENTS.append(
        {
            "date": datetime.utcnow().date().isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "identity": identity,
        }
    )
    # Best-effort push into backend audit trail
    try:
        headers = {"Authorization": f'Bearer {session["access_token"]}'}
        requests.post(
            f"{API_BASE_URL}/audit/logs",
            headers=headers,
            json={
                "action": "EMERGENCY_ALERT_SENT",
                "resource_type": "governance_guard",
                "resource_id": identity or "n/a",
                "new_value": context,
            },
            timeout=5,
        )
    except Exception:
        pass
    flash("Emergency alert sent to governance report queue.")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
