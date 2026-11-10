# 既有工具接入

2026-11-04 搜尋本機工具目錄與技能索引，未找到已登記的淘寶專用工具；索引有時間差，使用前仍應查當前工具。現場實際成功入口為 Playwright MCP 的分頁、導覽、頁面快照與圖片讀取。

## 整合結果

唯一讀取程式為 `../scripts/read-marketplace.js`，在現有 Playwright MCP 的 `browser_run_code_unsafe` 執行。技能在 Claude、Codex 與 Orca 使用相同實體檔，不是四份程式。沒有新增常駐服務或第二套瀏覽器。

| 原有能力 | 整合後 |
| --- | --- |
| A 的商品集中讀取與分類圖片分頁 | 同一次讀取商品、參數、款式與圖片，圖片有界分頁 |
| A 的登入初始化與 B 的登入檢查 | 只檢查同一個瀏覽器；需要掃碼時沿用現有 MCP 頁面 |
| B 的京東／淘寶搜尋與商品讀取 | 同一程式依當前網站讀取商品或搜尋結果 |
| B 的評價讀取 | 讀已載入的評價內容與明示分數；不以用詞猜測好壞 |
| B 的截圖、滾動、分頁與導覽 | 重用現有 Playwright MCP，不重寫瀏覽器控制器 |
| 兩套各自的持久登入與商品快取 | 不建立第二套登入，不快取可能跨款式錯配的價格 |

這是功能整合與單一執行入口，不是把兩個 Python server 同時包起來。未採用上游 A 的無界自動抓完與反偵測功能。問答、未載入評價與圖片 OCR 沒有自動完成；需要時沿用頁面及看圖工具，不能假稱已驗證。

## 選擇順序

1. 前文使用且目前能操作的已登入瀏覽器。Playwright 用 `browser_tabs`、`browser_navigate`、`browser_snapshot`，必要時 `browser_evaluate` 讀商品及圖片；依工具當前 schema 呼叫，不臆造參數。
2. 已安裝的淘寶專用 MCP 若持有原登入，可使用；先確認狀態，再抓商品。它與 Playwright 的登入不能假定互通。
3. 原本使用 Claude in Chrome 時，載入該工具隨附的 chrome-browser 技能，依它取得當前分頁；不複製另一份瀏覽器操作規則。
4. 只有可見桌面可用時，使用既有 computer-use 技能。換瀏覽器不代表登入也跟著移動。

## 上游來源與授權

- [JeremyDong22/taobao_mcp](https://github.com/JeremyDong22/taobao_mcp)：README 提供 `taobao_initialize_login` 與 `taobao_fetch_product_info`，並宣稱保存登入。若此 MCP 已啟用，依它的初始化流程確認，再讀商品；不要為取代正常運作的原瀏覽器而重新登入。
- [HaonanYu123/JD-Taobao-MCP](https://github.com/HaonanYu123/JD-Taobao-MCP)：README 提供 `browser_status`、`check_login`、`get_product_detail`，預設獨立 `BROWSER_PROFILE_DIR`，且預設關閉改變帳戶或交易的操作。若已有原 session，先 status/check_login，不先 open_login。

2026-11-05 已讀原碼：A 固定版本 `4cdeb50297929f76e15704e812a3aa15e050919c`，B 固定版本 `63a4e143ad54d1d7ea9d7fa85615283beaaf3f1d`。A 未找到 LICENSE 或明確授權，沒有複製其程式；B 的 LICENSE 為 MIT。整合器為自行實作，未直接搬入任一上游原碼或依賴，兩套上游服務均未安裝。

## 驗收與邊界

- Node 測試：非法圖片批次、非購物網站及假網域、不安全協定、瀏覽器錯誤不得偽裝成登出。
- `tests/verify-browser.js` 使用新測試分頁與本機攔截資料，15 項真 DOM 檢查；不發網站請求、不登入。將整合器與此測試函式分別讀入 `read`、`verify`，在 MCP 執行 `async (page) => { const read = <完整整合器>; const verify = <完整測試函式>; return verify(page, read); }`。測試結束關閉自己的分頁。
- 陰性對照：刻意移除登入帳戶文字確認後，第一項測試因「我的淘寶連結不誤判成已登入」失敗，證明測試能抓出這個誤判。
- 真淘寶兩商品讀回：`1081312377145/6300910807066` 為雙 V100 32GB、14599；`1075959665126/6126359180773` 為雙 V100 32GB、15999，均讀到已登入及一年保固。第二款通用參數另寫 16GB × 2，與所選款式不同，輸出保留兩者，不能自行消除矛盾。
- 京東、搜尋結果及評價目前驗到本機瀏覽器資料；真淘寶搜尋頁要求人工驗證，整合器回傳 `verification_required` 後停止，未繞過或重試。尚未做真人京東登入或公開搜尋完整驗收。未進行購買、加購、傳訊息或正式服務部署。
- 本次直接工具結果摘要見 [verification.json](verification.json)；它只證明記錄當時，不能當未來頁面或登入狀態。
