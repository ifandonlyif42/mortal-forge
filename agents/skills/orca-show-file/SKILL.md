---
name: orca-show-file
description: 使用者在 Mac 或遠端連回來、打不開本機 file:// 連結時，把 PDF、圖片等檔案開在 Orca 視窗分頁讓他直接看。要「給連結」或「讓我看檔案」且使用者可能不在本機時使用。
---

file:// 連結只在這台電腦有效；遠端使用者看的是 Orca 視窗，所以改開 Orca 分頁（使用者 2026-11-05 確認 PDF 可看）。

1. 檔案必須在目前專案資料夾內，Orca 只收專案內相對路徑，否則回 invalid_relative_path。
2. 檔案在專案外就複製到專案內的 tmp-pdf/，用英文 ASCII 檔名。
3. 在專案根目錄執行 `orca file open tmp-pdf/檔名.pdf --focus`；使用者要看檔案才加 --focus。
4. 回報檔名與位置，並說明複製的檔案是未追蹤檔，看完可刪；不要自動 commit。

限制：只確認 PDF 可開；其他格式未驗證。不上傳外部服務。
