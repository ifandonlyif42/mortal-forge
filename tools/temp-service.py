#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path.home()
STATE = HOME / ".agents" / "temp-services"
LOGS = STATE / "logs"
FORMAT = "%Y-%m-%dT%H:%M:%S"
TTL = re.compile(r"^(\d+)([mhd])$")


def parse_ttl(text):
    match = TTL.match(text)
    if not match:
        raise SystemExit("ttl 格式：30m、4h、1d")
    value = int(match.group(1))
    unit = {"m": 60, "h": 3600, "d": 86400}[match.group(2)]
    return timedelta(seconds=value * unit)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        return Path(f"/proc/{pid}/stat").read_text().split(")")[-1].split()[0] != "Z"
    except OSError:
        return False


def records():
    STATE.mkdir(parents=True, exist_ok=True)
    found = []
    for path in sorted(STATE.glob("*.json")):
        try:
            found.append((path, json.loads(path.read_text())))
        except ValueError:
            continue
    return found


def ports(pgid):
    out = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout
    mine = set()
    for line in out.splitlines():
        for pid in re.findall(r"pid=(\d+)", line):
            try:
                if os.getpgid(int(pid)) == pgid:
                    mine.add(line.split()[3].rsplit(":", 1)[-1])
            except OSError:
                continue
    return sorted(mine)


def stop_record(path, record):
    pgid = record["pgid"]
    if alive(record["pid"]):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        for _ in range(20):
            if not alive(record["pid"]):
                break
            time.sleep(0.25)
        if alive(record["pid"]):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if record.get("on_stop"):
        result = subprocess.run(record["on_stop"], shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"{record['name']} on-stop 失敗：{result.stderr.strip()[:200]}", file=sys.stderr)
    path.unlink(missing_ok=True)


def start(args):
    if not args.command:
        raise SystemExit("缺少要執行的指令")
    STATE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    path = STATE / f"{args.name}.json"
    if path.exists():
        old = json.loads(path.read_text())
        if alive(old["pid"]):
            raise SystemExit(f"{args.name} 已在執行（pid {old['pid']}），先 stop 或換名稱")
        path.unlink()
    log = open(LOGS / f"{args.name}.log", "ab")
    proc = subprocess.Popen(args.command, cwd=os.getcwd(), stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    now = datetime.now()
    record = {
        "name": args.name,
        "pid": proc.pid,
        "pgid": os.getpgid(proc.pid),
        "cwd": os.getcwd(),
        "command": " ".join(args.command),
        "started": now.strftime(FORMAT),
        "expires": (now + parse_ttl(args.ttl)).strftime(FORMAT),
        "on_stop": args.on_stop or "",
        "purpose": args.purpose or "",
    }
    path.write_text(json.dumps(record, ensure_ascii=False))
    print(f"{args.name} pid={proc.pid} 到期 {record['expires']} log={LOGS / (args.name + '.log')}")


def listing(_):
    rows = records()
    if not rows:
        print("沒有登記的臨時服務")
    for _path, record in rows:
        state = "執行中" if alive(record["pid"]) else "已結束"
        print(f"{record['name']}\t{state}\t埠 {','.join(ports(record['pgid'])) or '-'}\t到期 {record['expires']}\t{record['cwd']}\t{record['purpose']}")


def stop(args):
    for path, record in records():
        if args.name == "all" or record["name"] == args.name:
            stop_record(path, record)
            print(f"已停止 {record['name']}")


def reap(_):
    now = datetime.now().strftime(FORMAT)
    for path, record in records():
        if record["expires"] <= now or not alive(record["pid"]):
            stop_record(path, record)
            print(f"已回收 {record['name']}（{'到期' if record['expires'] <= now else '程序已結束'}）")


def group_ticks(pgid):
    total = 0
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if int(fields[2]) == pgid:
            total += int(fields[11]) + int(fields[12])
    return total


def connected(pgid):
    mine = set(ports(pgid))
    if not mine:
        return False
    out = subprocess.run(["ss", "-tnH", "state", "established"], capture_output=True, text=True).stdout
    return any(line.split()[2].rsplit(":", 1)[-1] in mine for line in out.splitlines() if len(line.split()) >= 4)


def sweep(args):
    STATE.mkdir(parents=True, exist_ok=True)
    lock = open(STATE / ".sweep.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return
    limit = parse_ttl(args.idle)
    now = datetime.now()
    for path, record in records():
        if not alive(record["pid"]):
            stop_record(path, record)
            print(f"已回收 {record['name']}（程序已結束）", file=sys.stderr)
            continue
        if record["expires"] <= now.strftime(FORMAT):
            stop_record(path, record)
            print(f"已關閉 {record['name']}（到期）", file=sys.stderr)
            continue
        ticks = group_ticks(record["pgid"])
        log = LOGS / f"{record['name']}.log"
        log_time = datetime.fromtimestamp(log.stat().st_mtime) if log.exists() else datetime.min
        last = datetime.strptime(record.get("last_active", record["started"]), FORMAT)
        if ticks != record.get("last_ticks") or connected(record["pgid"]) or log_time > last:
            last = now
        record["last_active"] = last.strftime(FORMAT)
        record["last_ticks"] = ticks
        if now - last > limit:
            stop_record(path, record)
            print(f"已關閉 {record['name']}（閒置超過 {args.idle}）", file=sys.stderr)
        else:
            path.write_text(json.dumps(record, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="登記並定期回收臨時開出來的本機服務")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("start")
    p.add_argument("--name", required=True)
    p.add_argument("--ttl", required=True)
    p.add_argument("--purpose")
    p.add_argument("--on-stop")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.set_defaults(run=start)
    sub.add_parser("list").set_defaults(run=listing)
    p = sub.add_parser("stop")
    p.add_argument("name")
    p.set_defaults(run=stop)
    sub.add_parser("reap").set_defaults(run=reap)
    p = sub.add_parser("sweep")
    p.add_argument("--idle", default="30m")
    p.set_defaults(run=sweep)
    args = parser.parse_args()
    if args.action == "start" and args.command[:1] == ["--"]:
        args.command = args.command[1:]
    args.run(args)


if __name__ == "__main__":
    main()
