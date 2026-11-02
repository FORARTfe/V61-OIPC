# Stock firmware analysis and OpenIPC porting considerations for Hi3516A PTZ

Analysis date: 2026-11-02. Scope: static inspection of a user-provided firmware image. No vendor binaries were executed; no hardware was accessed or modified. Conclusions derived from boot scripts and firmware contents are distinguished from things still needing on-device verification.

## 1. Identification and integrity

- Source filename: [V61S_F5.HI_V6.3.72_24M_20250424.img](https://downloads.ptzoptics.com/firmware/ndi-sdi-g2-12x)
- Exact size: 25,690,112 bytes = 24.50 MiB (`0x01880000`).
- SHA-256: `48deb67e8fbbb26c0b4528ae957711042d4bea81059cf05b5475943024b43448`.
- U-Boot 2010.06 code is present; the embedded build string is dated 2019-11-14.
- Linux ARM 3.4.35 appears as a gzip-compressed legacy U-Boot `uImage`.
- The root filesystem is JFFS2.
- `/home/devinfo.conf` identifies the product configuration as `NEOiD PTZ NDI 20X`, `V60` family. This is evidence about the installed software, not proof of the exact PCB hardware revision.
- Vendor kernel modules (for example, `hi3516a_isp.ko`) report a `3.4.35 mod_unload ARMv7 p2v8` vermagic. They cannot be assumed to load unchanged on the 4.9.37 OpenIPC kernel discussed in the upstream configuration.

A diagnostic JFFS2 node scanner reconstructed an inventory and about 745 file/symlink payloads from the source image. It does not represent a complete recovery of all runtime state. The source image and extracted vendor payloads are not redistributed here.

## 2. Stock partition map

U-Boot defaults found as strings in the stock image:

```text
bootargs=mem=256M console=ttyAMA0,115200 root=/dev/mtdblock2 rootfstype=jffs2 mtdparts=hi_sfc:512K(boot),3M(kernel),20M(rootfs),1M(reserve),512K(data)
bootcmd=sf probe 0;sf read 0x82000000 0x80000 0x300000;bootm 0x82000000
```

| MTD index | Partition | Offset | Size | End (exclusive) |
|---|---|---|---|---|
| mtd0 | boot | `0x00000000` | 512 KiB | `0x00080000` |
| mtd1 | kernel | `0x00080000` | 3 MiB | `0x00380000` |
| mtd2 | rootfs | `0x00380000` | 20 MiB | `0x01780000` |
| mtd3 | reserve | `0x01780000` | 1 MiB | `0x01880000` |
| mtd4 | data | `0x01880000` | 512 KiB | `0x01900000` |

The update image ends at `0x01880000`, exactly where the `data` partition begins. The contents of a real device's `/data` partition are therefore not supplied by this file. It is an update image, not a verified full-flash backup.

The vendor `/etc/fw_env.config` describes a U-Boot environment at `/dev/mtd0`, offset `0x60000`, size `0x20000`, sector size `0x20000`. This identifies an expected location, not the live environment content. The corresponding image region is not a usable backup of the settings held on a real camera.

The specified partitions occupy at least 25 MiB of address space. A 32 MiB SPI NOR device is a plausible hypothesis, but its true capacity, JEDEC ID and erase layout are unverified without `/proc/mtd`, kernel logs or chip markings. A generic 8 MiB OpenIPC profile does not match this partition plan.

## 3. Boot chain and stock startup

Observed intended sequence:

```text
U-Boot
  -> Linux 3.4.35 uImage
  -> JFFS2 root on /dev/mtdblock2
  -> /etc/init.d/rcS
  -> mount JFFS2 /dev/mtdblock4 at /data
  -> /home/vhd_start.sh
  -> proprietary media, network, web and PTZ applications
```

Among other actions, `/home/vhd_start.sh` calls the platform loader with:

```sh
/home/ko/load3516a -a -sensor mn34220 -osmem 256 -online
```

The startup script subsequently launches the network command service, GPIO initialization, `lighttpd`, the `v600_hi3516a` application, and vendor upgrade/management processes. The stock ONVIF `nvt` service is enabled conditionally by `/data/netport.conf`. A separate `autofocus` invocation is commented out: its presence alone does not establish the precise operational focus mechanism.

The stock platform loader declares 512 MiB total memory split into 256 MiB for Linux (`mem=256M`) plus a 256 MiB multimedia zone, `mmz_start=0x90000000`. These are software declarations. Actual DDR size and physical mapping must be verified on the running board before use with OpenIPC.

## 4. Panasonic MN34220 sensor and video pipeline

- Sensor selected at boot: `mn34220`, consistent with Panasonic MN34220.
- Sensor control: I2C0, with stock pinmux values `0x200f0050=0x2` (SCL) and `0x200f0054=0x2` (SDA).
- Stock register programming includes `0x2003002c=0x90007`; vendor comments describe a 37.125 MHz sensor clock and a 250 MHz VI clock.
- Stock ISP tuning appears in `/home/configs/mn34220_cfg.ini`, including AE/AWB/ISP parameters; the vendor file is not shipped here.
- `/home/ko/load3516a`, `/home/ko/pinmux_hi3516a.sh` and `/home/ko/clkcfg_hi3516a.sh` configure clocks, pinmux and proprietary media modules (ISP, VI, VPSS, VENC and associated devices).

The [OpenHisilicon](https://github.com/OpenIPC/openhisilicon) upstream project has documented support material relating to MN34220 in the Hi3516AV100 sensor library family. That is a promising basis, not proof that a ready-built OpenIPC image for this specific board will use the correct driver, sensor interface, image parameters or timing. Confirm library build, packaging, sensor power/reset controls, physical lane configuration, Bayer order, and the expected output resolution/frame rate. A name in a sensor library list is not an end-to-end test.

The stock ISP tuning file is useful as private reference material but cannot safely be copied blindly into an unrelated ISP userspace version.

## 5. PTZ hardware and the separate STM32-class MCU

Evidence from stock application and maintenance binary strings includes:

- `/home/v600_hi3516a` references `/dev/ttyAMA1`, `stm32_fd`, `send_to_stm32`, `ptzposition.dat`, Pelco-P, Pelco-D and a VISCA-over-IP listener using UDP port 52381.
- `/home/upgrade` and `/home/arm_upgrade` reference entering STM32 upgrade mode, resetting STM32, `stm32flashloader.c`, and `/dev/ttyAMA1`.
- The separate vendor file `/home/V610_V61_ARM_6.4.20SHI.bin` has length 147,160 bytes and starts with little-endian words `0x20000400`, `0x08000147`, `0x0800BD95`, `0x08005649`, consistent with a Cortex-M vector table / STM32-style firmware layout. This does not identify the MCU model conclusively.
- The application references persistent records such as `/data/ptzposition.dat`, `/data/guardposition.dat` and `/data/lens_parameter.dat`. The actual `/data` partition is not available in the update image.

Likely command architecture:

```text
VISCA-over-IP / ONVIF / other network control
                      |
          Stock Hi3516A application
                      |
             UART1 /dev/ttyAMA1
                      |
                 MCU (STM32)
                      |
       Pan/Tilt/Zoom/Focus hardware
```

This strongly suggests that at least part of the low-level motor and lens control resides on the secondary MCU. Porting PTZ to OpenIPC calls for a service that understands the serial protocol, not necessarily for an entirely new stepper-motor driver. However, neither the MCU's responsibilities nor its frame format is fully established by static analysis.

The stock software's use of the term VISCA does not imply that its internal Hi3516A-to-MCU UART frames follow standard VISCA. The generic OpenIPC `motors` package should not be assumed compatible with this vendor's firmware.

Suggested reverse-engineering sequence on the original running firmware:

1. Identify the electrical voltage, ground and direction of both UART lines with suitable measurement tools; capture passively at first.
2. Observe the boot-time handshake and idle traffic; establish baud rate, framing and checksums.
3. Capture brief, supervised and reversible commands: STOP, small PAN, small TILT, small ZOOM, position read if available.
4. Correlate packets with ACK/status data, motion speed and any periodic watchdog/heartbeat requirements.
5. Reproduce a minimal STOP-first implementation, protecting mechanical limits and calibrations.

Do not flash or invoke the MCU upgrade routines while the protocol or hardware revision is uncertain. `/dev/ttyAMA2` occurs in another program but cannot be reliably assigned to a particular interface from this image alone.

## 6. Feature compatibility assessment

| Feature | OpenIPC outlook | Missing or unverified requirement |
|---|---|---|
| Linux boot / Ethernet / SSH | Plausible with AV100 support | Board-specific DDR, SPI NOR, PHY, pinmux, DT and bootargs |
| RTSP / H.264 | Plausible | Working sensor, ISP/VI/encoder and Majestic integration |
| H.265 | Not established for this particular board/SoC | Confirm hardware encoder and supported media SDK |
| MN34220 video | Upstream foundation to investigate | Board-specific clocks/reset, ISP, sensor library, mode |
| Pan / Tilt | Not automatic | Vendor serial protocol and dedicated MCU bridge |
| Zoom / Focus / Autofocus | Not automatic | MCU protocol, lens parameters and calibration |
| PTZ presets | Requires integration | Persistent storage format and PTZ backend |
| ONVIF PTZ | Possible as a future layer | ONVIF server plus actual PTZ bridge |
| NDI / NDI HX | Not preserved merely by installing OpenIPC | SDK, licensing and integration |
| HDMI / SDI | Unproven | External output chips, drivers and media routing |

The script `/home/ko/pinmux_hi3516a.sh` selects `vo_bt1120_mode`, configuring VO pins for a BT.1120-style interface. This points toward a potential external video output path; it does not identify an HDMI or SDI transmitter.

The stock system uses third-party proprietary userspace executables and NDI-related libraries. Copying them to a newer OpenIPC userspace is not enough to establish ABI or kernel-driver compatibility. NDI and professional video outputs may be the main practical limitations of a fully equivalent replacement.

## 7. Staged porting plan

### Stage A — Inventory and recovery proof

On a camera running its original firmware, collect only read-oriented diagnostics first:

```sh
uname -a
cat /proc/cpuinfo
cat /proc/cmdline
cat /proc/mtd
cat /proc/meminfo
dmesg | grep -Ei 'spi|nor|mtd|hi3516|uart|eth|phy|mmz|i2c'
cat /proc/modules
ls -l /dev/ttyAMA* /dev/i2c* 2>/dev/null
fw_printenv
```

Some output may contain MAC/IP addresses, tokens, serial numbers and other device identifiers. Do not post unredacted results. Preserve a privately verified, complete dump of all actual flash partitions, especially U-Boot, environment, reserve and data; verify checksums and a known-good recovery mechanism (external SPI programmer or verified U-Boot path).

### Stage B — Reproducible OpenIPC baseline

On an x86_64 Linux build host, refer to the upstream workflow, for example:

```sh
git clone --depth 1 https://github.com/openipc/firmware
cd firmware
make BOARD=hi3516av100_lite br-hisilicon-opensdk
```

This command builds the documented OpenHisilicon SDK components and does not install OpenIPC on the camera. Verify the current upstream instructions and available build targets for the checkout in use.

The upstream `hi3516av100_lite_defconfig` researched at the time included `BR2_OPENIPC_FLASH_SIZE="8"`. This size does not fit the stock partition layout described above. Create a board-specific configuration after confirming the real SPI NOR capacity and physical geometry. OpenIPC's rootfs design is also different from the stock JFFS2 layout; do not copy stock `rootfstype=`/`root=` settings unchanged.

### Stage C — First recoverable boot

Retain the existing bootloader initially. With UART0 console (`ttyAMA0`, 115200 in stock bootargs), test an alternative kernel/rootfs via a temporary RAM/TFTP/NFS path only if the actual U-Boot supports it and the memory/boot arrangement is safe. Establish a functional rollback method before permanent storage changes. Verify SoC identification, memory and MMZ, network PHY, watchdog, I2C and UART1 pinmux/device-tree nodes.

### Stage D — First video

Enable compatible MN34220 sensor integration, clock/reset/power, I2C0 and HiSilicon VI/ISP/VENC modules. First target a stable H.264 stream; color tuning and advanced exposure can follow. Keep vendor ISP values only as local reference material.

### Stage E — PTZ and optional features

Capture and characterize the UART1 protocol. Implement a small separate service that limits motion, ensures STOP and exposes a local API. Add VISCA and ONVIF PTZ adapters later. Protect calibration and lens limits. Approach NDI and HDMI/SDI as separate, unproven features with license and chip-level dependencies.

### Stage F — Persistent installation

Only after temporary boot and recovery have been demonstrated should a verified per-board flash image be considered. Do not write a generic 8 MiB partition image over the stock layout or erase `mtd0`/`mtd4` on the basis of this research alone.

## 8. Technical conclusion

An OpenIPC-based IP video system with the MN34220 sensor is plausible. A working product needs a board-specific boot configuration, media pipeline validation and careful preservation of recovery options. Full PTZ needs independent analysis of the MCU's serial interface. An equivalent replacement preserving the original NDI, HDMI and SDI features has not been demonstrated. Next useful evidence: `/proc/mtd`, safe/redacted `fw_printenv`, boot logs, real flash chip marking/PCB images, and passive UART1 traces.

## Public upstream references (checked during original analysis: 2026-11-02)

- [OpenHisilicon: AV100 generation, SDK, build instructions and sensor support](https://github.com/OpenIPC/openhisilicon)
- [OpenHisilicon sensor driver API](https://github.com/OpenIPC/openhisilicon/blob/main/docs/sensor-driver-api.md)
- [OpenIPC AV100 Lite default configuration](https://github.com/OpenIPC/firmware/blob/master/br-ext-chip-hisilicon/configs/hi3516av100_lite_defconfig)
- [OpenIPC firmware: UART activation discussion](https://github.com/OpenIPC/firmware/issues/2219)
- [Older OpenIPC sensor list (not a complete modern support matrix)](https://github.com/OpenIPC/wiki/blob/master/en/guide-supported-sensors.md)

Source-specific evidence references and file checksums are listed in [Evidence manifest](EVIDENCE_MANIFEST.md). These paths describe files in the original update image; vendor files are not included in this public archive.
