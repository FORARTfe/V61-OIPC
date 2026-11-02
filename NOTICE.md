# Provenance, publication scope, and safety

This repository documents a static analysis of a firmware update file supplied by a device owner. The image is NOT included. The project is independent research and is not an official product release of OpenIPC, HiSilicon, Panasonic, NEOiD or any other vendor.

The original private research archive included files reconstructed from the vendor's JFFS2 root filesystem (startup shell scripts, ISP tuning configuration, a secondary MCU `.bin` file, and other assets). Those files are intentionally NOT packaged for public redistribution here. Instead, this project provides:

- A newly written English-language account of the findings and uncertainty.
- A names-and-metadata inventory of files discovered in the filesystem.
- A checksum and source-path manifest for independently identifying evidence if you possess the original image lawfully.
- An independent Python diagnostic script for static inspection.

The original image, proprietary firmware payloads and vendor scripts remain subject to their respective rights. The MIT license in this repository applies only to the original documentation and tools shipped here, not to the referenced vendor firmware or third-party projects.

No actual flash memory writes, live boot tests, serial packet captures, or on-device calibration checks were performed. Stock MTD parameters are not an automatically safe OpenIPC flash map. Do not use this repository as instructions to erase or overwrite U-Boot, environment, calibration, or `/data` partitions.

Security/privacy: never upload a real device's `/data` partition, U-Boot environment, account files, SSH keys, wireless configuration, serial numbers, access tokens, or unredacted production logs. A raw UART trace can also contain device-specific values: inspect before sharing.
