---
name: temp-service
description: 臨時開本機 dev server、watch、http.server 等服務時使用；必須登記並設到期時間，由計時器定期回收。
---

# 臨時本機服務登記

臨時開出來的服務（dev server、`tsx watch`、`http.server`、驗收用的 API 與 web）一律登記，不得直接啟動（使用者 2026-11-04 定）。起因：驗收開的 API 空跑 13 小時，還佔著測試資料庫。

- 啟動：`python3 ~/tools/temp-service.py start --name <名稱> --ttl <30m|4h|1d> --purpose <用途> [--on-stop "<收尾指令>"] -- <原指令>`。在要執行的目錄下執行；整組程序用同一個行程群組，停止時一起收。
- 收尾指令：服務用到臨時資料庫或容器時寫在 `--on-stop`，例如 `docker exec crossec-dev-postgres psql -U postgres -c 'DROP DATABASE crossec_xxx'`，停止或到期時自動跑。
- 查看：`list` 顯示名稱、狀態、埠、到期時間、目錄、用途。
- 停止：`stop <名稱>` 或 `stop all`。驗收做完立刻停，不留到下一輪。
- 閒置即關（使用者 2026-11-04 定）：每次執行 Bash 前，PreToolUse 會跑 `temp-service.py sweep`；`temp-service-reap.timer` 每 5 分鐘也跑一次。閒置＝連續 30 分鐘沒有 CPU 時間變化、沒有已建立的連線、log 也沒更新；符合就關掉並跑收尾指令。到期或程序已結束的登記同時回收。掃描失敗不擋 Bash。查看 `systemctl --user list-timers temp-service-reap.timer`。
- 守門：`~/.agents/guards/temp_service_guard.py` 擋直接執行 `pnpm dev`、`next dev`、`tsx watch`、`vite`、`python -m http.server`（結束碼 2）；經 `temp-service.py` 啟動的不擋。測試 `python3 -m unittest test_temp_service_guard`。
- 容器不在此登記：Docker 容器與磁碟區用 `--rm` 或 `--label expire=`，由 `docker-expire.timer` 回收。
- 邊界：閒置只掃有登記的服務，不碰未登記的程序（可能是使用者自己的，如 helios、vite）。瀏覽器開著的連線會算「有連線」而不被關。守門只看指令字串。`scripts/dev-up.sh` 這類自己在背景再啟動服務的腳本不在登記內，用完照專案規定跑 `--stop`；包在腳本裡啟動的 dev server 也擋不到。
