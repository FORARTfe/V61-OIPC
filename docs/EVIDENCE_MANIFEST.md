# Evidence manifest (references only)

The following paths refer to the JFFS2 root filesystem reconstructed from the stock update image. No original vendor files are included in this public package. Hashes are provided solely for locally verifying independently extracted evidence.

Original firmware image SHA-256: `48deb67e8fbbb26c0b4528ae957711042d4bea81059cf05b5475943024b43448`.

| Path inside original rootfs | Bytes | SHA-256 |
|---|---:|---|
| `/etc/fw_env.config` | 437 | `629997223b698a86fdc8c2b2e611d5f4cfb390546b50e656d3564c7bd9d6b542` |
| `/etc/init.d/rcS` | 1,251 | `4785291273b8ffb9f3f273c5cecfdf21f4de8ba994b7f851c26fa0f551d43069` |
| `/etc/inittab` | 3,399 | `4e7167b7f808db906ceecbc451d75f9a539a5ef48d1f7306bad9dbb14d455d53` |
| `/home/V610_V61_ARM_6.4.20SHI.bin` | 147,160 | `c8d8eb4b04cb37352e6d5c50b8ee15e01aa79089d39dda0284101030f50119a0` |
| `/home/configs/mn34220_cfg.ini` | 14,548 | `6a0226b86e0e252fea4e22d2becc5ca6f64c0e667d5751aa813438ca80bdd02c` |
| `/home/devinfo.conf` | 47 | `38871ebb79434e497712339b9627b981f6f24b1982774399b2ce8e9c07b9cf0d` |
| `/home/ko/clkcfg_hi3516a.sh` | 1,702 | `d836f5eeba55f96072e85a52fc14506a730e594c380fd3f357eb65ca2d84e365` |
| `/home/ko/load3516a` | 9,248 | `da7cecfa0d8981e08ca39e27b56e7ad7c04bb22a035c380589f6588407ae84dd` |
| `/home/ko/pinmux_hi3516a.sh` | 2,225 | `fa41933dbd4afafdbad1e76702146e123c75f3e21b767bd69c622e29a8887d81` |
| `/home/ndi_version_file` | 6 | `c3d62fdfbf5052f7064fc4e81f572e41ad524a8e761895a0fc891cebe84dda3a` |
| `/home/vhd_start.sh` | 2,802 | `e4edb5fc0ff997f4119aafb6bb2848202674f8c84e9ee9c2d3b5b23090988ba5` |

The `V610_V61_ARM_6.4.20SHI.bin` row is a referenced vendor microcontroller image. The SHA-256 does not confer any right to redistribute or flash it.

## Why the original payloads are excluded

- The vendor MCU image and executable scripts/configuration are potentially copyrighted third-party works and are unnecessary for discussing the port publicly.
- Device-specific MTD partition `/data` is not contained in the source update image and may contain private identifiers or calibration data on an actual camera.
- The public inventory in `data/file_inventory.tsv` contains filenames, inode numbers, mode, size, fragment count and compression IDs, but not file contents.
- The `data/metadata.json` file was regenerated using the Python tool in this repository with scanning limited to the 20 MiB rootfs area; the original private scanner also examined the following reserve region and found more clean markers.

## Cross-checking in private

Run `python3 tools/inspect_firmware.py /path/to/firmware.img --output ./local-analysis --extract-rootfs` outside a public Git checkout, then compare a file digest with this table. Extraction writes regular files, not symbolic links. Do not upload the results or unredacted device settings.

## Supporting observations from the vendor files

| Claim | Local evidence path(s) |
|---|---|
| Product family `NEOiD PTZ NDI 20X` / `V60` | `/home/devinfo.conf` |
| Selected sensor `mn34220`, startup sequence | `/home/vhd_start.sh`, `/home/ko/load3516a` |
| I2C0 sensor pins and 37.125 MHz sensor clock setting | `/home/ko/load3516a`, `/home/ko/clkcfg_hi3516a.sh` |
| BT.1120 video-output pinmux | `/home/ko/pinmux_hi3516a.sh` |
| Stock ISP parameters | `/home/configs/mn34220_cfg.ini` |
| Persistent data mounted from MTD block 4 | `/etc/init.d/rcS` |
| U-Boot environment location | `/etc/fw_env.config` |
| Separate MCU firmware candidate | `/home/V610_V61_ARM_6.4.20SHI.bin` |
| UART1, MCU control and VISCA/Pelco handlers | Strings in stock `/home/v600_hi3516a` and updater applications; not distributed here |
