# claude-pcb — RP2350A 搭載 Raspberry Pi Pico 互換基板

Claude (Fable 5.2) が KiCad 10 で設計している、RP2350A を使った Raspberry Pi Pico 互換基板です。
回路図も基板も Python スクリプトから生成しており、作業工程は [docs/LOG.md](docs/LOG.md) の制作ログに残しています。

## 仕様（予定）

| 項目 | 内容 |
| --- | --- |
| MCU | RP2350A (QFN-60) |
| 外形 | 21 × 51 mm、Pico と同じ 40 ピン配置（2.54mm ピッチ、端面スルーホール付き） |
| USB | Type-C（USB 2.0、CC 5.1kΩ） |
| Flash | QSPI 4MB (USON-8 2×3mm) |
| 電源 | VBUS → ショットキー → VSYS → 昇降圧 DC/DC (TPS63001) → 3.3V |
| コア電源 | RP2350 内蔵スイッチングレギュレータ (3.3µH) → 1.1V |
| その他 | BOOTSEL ボタン、LED (GPIO25)、VBUS 検出 (GPIO24)、VSYS/3 測定 (GPIO29)、SWD 3 ピン |
| 基板 | 4 層 (信号 / GND / 電源 / 信号)、部品は表面のみ |

純正 Pico との違い: USB が Type-C のため、コネクタ両脇の上側取付穴 2 つはありません（下側 2 つは同じ位置）。

## 構成

- `tools/` — 生成スクリプトと補助ツール
- `hardware/` — KiCad プロジェクト（生成物）
- `docs/LOG.md` — 制作ログ
