# OpenIPC porting research: HiSilicon Hi3516A PTZ camera

Community-oriented, static firmware research for an OpenIPC port to a HiSilicon Hi3516A-based PTZ camera. The stock software identifies the platform as `NEOiD PTZ NDI 20X` (`V60` family) and selects a Panasonic `MN34220` image sensor.

Status: research / preliminary porting plan. This repository is **not** a tested OpenIPC firmware image, board support package, or flashing guide. Neither the original device nor an OpenIPC boot was tested during this analysis.


## Repository contents

```text
docs/FIRMWARE_ANALYSIS.md       Full technical analysis in English
docs/PORTING_CHECKLIST.md       Safe, staged OpenIPC porting checklist
docs/EVIDENCE_MANIFEST.md      Source-file references and checksums (no vendor payloads)
data/metadata.json             Machine-readable summary of static findings
data/file_inventory.tsv        Names/sizes/modes from the JFFS2 filesystem
tools/inspect_firmware.py      Standalone, read-only-by-default analysis tool
tests/test_inspector.py        Basic tests for the analyzer
```

## Key findings

| Area | Finding | Confidence / caveat |
|---|---|---|
| SoC | HiSilicon Hi3516A family, target OpenIPC `hi3516av100_lite` as a starting point | Board revision must be checked |
| Bootloader | U-Boot 2010.06 | Found in the source image |
| Linux | 3.4.35 ARM `uImage`, gzip compressed | Stock kernel, not reusable as OpenIPC module ABI |
| Filesystem | JFFS2 | Stock layout, not the OpenIPC filesystem layout |
| Sensor | Panasonic MN34220, I2C0, stock clock setting 37.125 MHz | Selected by stock boot script |
| RAM allocation | `mem=256M`; stock loader specifies 256 MiB MMZ, 512 MiB combined | Configuration only; actual RAM needs on-device validation |
| PTZ control | Hi3516A application -> `/dev/ttyAMA1` -> external STM32-class MCU | Serial protocol remains unknown |
| Video output | Stock pinmux configures BT.1120 | External HDMI/SDI chipset not identified |
| Persistent data | `/data` corresponds to MTD partition 4, absent from update image | Full flash backup still required |

## Reproduce the static analysis

Requirements: Python 3.9+; standard library only. Use a local, lawfully obtained firmware image. Do not commit the image, extracted blobs, or device backups.

```sh
python3 tools/inspect_firmware.py /path/to/V61S_F5.HI_V6.3.72_24M_20250424.img --output ./local-analysis
```

The script reads the image and writes a metadata JSON file and a filesystem inventory. It does not execute firmware code or flash any device. If you need extracted files for private analysis, pass `--extract-rootfs` and keep the resulting files outside version control.

```sh
python3 tools/inspect_firmware.py /path/to/firmware.img --output ./local-analysis --extract-rootfs
python3 -m unittest discover -s tests -v
```

By default the expected JFFS2 offset is `0x380000`. You can override the offset with `--rootfs-offset`; see `--help`. This parser is diagnostic rather than a general-purpose, security-hardened JFFS2 implementation; cross-check results before making hardware changes.

## Proposed OpenIPC approach

1. Capture `/proc/mtd`, `fw_printenv`, boot logs, RAM information, and board/flash-chip photos from the original device. Keep backups private.
2. Build the OpenIPC AV100 baseline as a starting point, not as a ready-to-flash image.
3. Define the actual flash map, memory map, device tree and recovery procedure.
4. Boot a temporary/recoverable system, where supported, before writing to SPI NOR.
5. Bring up the MN34220 sensor and a stable H.264 video stream.
6. Reverse-engineer the stock UART1-to-STM32 PTZ protocol by passive capture, then implement a small bridge service.
7. Treat NDI, HDMI/SDI and camera-specific optics as separate, currently unproven workstreams.

For details, read [Firmware analysis](docs/FIRMWARE_ANALYSIS.md) and [Porting checklist](docs/PORTING_CHECKLIST.md).

## Upstream references

- [OpenIPC firmware](https://github.com/OpenIPC/firmware)
- [OpenHisilicon project](https://github.com/OpenIPC/openhisilicon)
- [OpenHisilicon sensor driver API](https://github.com/OpenIPC/openhisilicon/blob/main/docs/sensor-driver-api.md)
- [Hi3516AV100 Lite defconfig](https://github.com/OpenIPC/firmware/blob/master/br-ext-chip-hisilicon/configs/hi3516av100_lite_defconfig)
- [OpenIPC UART1 device tree discussion](https://github.com/OpenIPC/firmware/issues/2219)

External links and compatibility information reflect research carried out on 2026-11-02; upstream versions may have changed.

## Contributions

Useful contributions include photos of the PCB and non-sensitive boot logs, SPI NOR identification, sensor interface details, UART1 electrical/packet captures (without private identifiers), and working OpenIPC configuration changes. Please never publish credentials, original device backups, vendor MCU firmware, or third-party source/binaries without redistribution rights.
