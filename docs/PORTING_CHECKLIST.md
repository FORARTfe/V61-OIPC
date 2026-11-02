# Porting checklist — Hi3516A / MN34220 / external PTZ MCU

This checklist deliberately separates what the update image shows from what must be confirmed on the running camera. It is not a flashing procedure.

## Before any write to flash

- [ ] Identify the real SoC package, PCB revision, SPI NOR part number, and chip capacity.
- [ ] Save serial console output from power-on through Linux init; redact device identifiers.
- [ ] Check the actual `/proc/mtd` against the stock defaults documented in `FIRMWARE_ANALYSIS.md`.
- [ ] Record kernel command line and real memory/DDR information; verify MMZ requirements.
- [ ] Save and validate U-Boot environment, bootloader, reserve and `/data` partitions privately.
- [ ] Establish a verified out-of-band recovery path (such as a compatible SPI NOR programmer).
- [ ] Document which camera features are mandatory: streaming, motor controls, autofocus, NDI, SDI/HDMI.

## Baseline software / board support

- [ ] Pin a known OpenIPC/OpenHisilicon revision and reproduce the AV100 toolchain build.
- [ ] Create a board-specific configuration: do not reuse the generic 8 MiB flash assumption.
- [ ] Match the rootfs partitioning and read-only/writable-overlay strategy to actual flash geometry.
- [ ] Confirm UART0 console and UART1 pinmux / device-tree enablement.
- [ ] Verify clocks, watchdog, Ethernet PHY, and working login/network.
- [ ] Prove a temporary boot and an unambiguous rollback before permanent installation.

## Video sensor

- [ ] Check whether an MN34220 AV100 library is built and installed by the selected firmware tree.
- [ ] Determine sensor interface type and wiring (MIPI/DVP, lanes, reset, power sequencing).
- [ ] Confirm I2C0 addressing, register timing, clock mode and Bayer order.
- [ ] Get VI/ISP/VENC working without PTZ motor activity.
- [ ] Verify a stable H.264 stream and realistic frame rate/resolution on actual hardware.
- [ ] Capture logs needed to diagnose ISP initialization issues, excluding private identifiers.

## PTZ microcontroller

- [ ] Identify UART1 voltage levels and TX/RX direction; do not connect 5 V logic to 3.3 V UART.
- [ ] Perform passive capture before attempting any active serial writes.
- [ ] Identify UART parameters and checksum/packet framing from normal stock operation.
- [ ] Document STOP, PAN, TILT, ZOOM and optional focus/preset commands.
- [ ] Identify motor travel limits, watchdog and calibration/preset state.
- [ ] Implement and test emergency STOP and limited-speed commands first.
- [ ] Keep STM32 firmware unchanged until the hardware and update mechanism are verified.
- [ ] Integrate the bridge with a controlled local API, then ONVIF/VISCA adapters.

## Optional hardware/software features

- [ ] Identify external BT.1120/HDMI/SDI chips on the board.
- [ ] Assess video output support separately from RTSP streaming.
- [ ] Review NDI software and licensing before attempting migration.
- [ ] Investigate PTZ presets, homing, autofocus and persistent lens calibration independently.

## Share results safely

Useful public contributions include sanitized logs, PCB photos with identifying labels obscured if necessary, flash chip model, sensor interface diagrams and analyzer-derived metadata. Do not upload the original image, extracted vendor binaries, real device settings, credentials, MAC addresses, personal data or proprietary MCU binaries.
