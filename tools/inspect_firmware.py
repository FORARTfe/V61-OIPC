#!/usr/bin/env python3
"""Static, read-only-by-default inspector for the documented Hi3516A image.

No firmware is executed. This is a diagnostic JFFS2 reconstruction, not a
complete JFFS2 implementation and not a flash / upgrade tool.
"""

import argparse
import collections
import hashlib
import json
from pathlib import Path
import stat
import struct
import sys
import zlib

DEFAULT_ROOTFS_OFFSET = 0x00380000
DEFAULT_ROOTFS_LENGTH = 0x01400000  # 20 MiB declared in stock bootargs
UIMAGE_OFFSET = 0x00080000
UIMAGE_MAGIC = 0x27051956
JFFS_MAGIC = b"\x85\x19"
MAX_FILE_SIZE = 64 * 1024 * 1024


def jffs_crc(data):
    """CRC as checked by the original diagnostic image parser."""
    return (zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF) & 0xFFFFFFFF


def inspect_uimage(image):
    header = image[UIMAGE_OFFSET:UIMAGE_OFFSET + 64]
    if len(header) != 64:
        return {"found": False, "reason": "image too short"}
    fields = struct.unpack(">7I4B32s", header)
    magic, hdr_crc, timestamp, payload_size, load, entry, payload_crc = fields[:7]
    if magic != UIMAGE_MAGIC:
        return {"found": False, "reason": "no legacy U-Boot uImage at expected offset"}
    zeroed_crc = header[:4] + b"\x00\x00\x00\x00" + header[8:]
    payload = image[UIMAGE_OFFSET + 64:UIMAGE_OFFSET + 64 + payload_size]
    return {
        "found": True,
        "offset": hex(UIMAGE_OFFSET),
        "name": fields[-1].split(b"\x00", 1)[0].decode("ascii", "replace"),
        "timestamp_unix": timestamp,
        "payload_size": payload_size,
        "load_address": hex(load),
        "entry_address": hex(entry),
        "header_crc_valid": (zlib.crc32(zeroed_crc) & 0xFFFFFFFF) == hdr_crc,
        "data_crc_valid": len(payload) == payload_size and (zlib.crc32(payload) & 0xFFFFFFFF) == payload_crc,
        "os_id": fields[7],
        "arch_id": fields[8],
        "image_type": fields[9],
        "compression_id": fields[10],
    }


def scan_jffs2(image, base, limit):
    """Rebuild a best-effort path list and inode-fragment index."""
    fs = memoryview(image)[base:min(len(image), base + limit)]
    pos = 0
    directories = {}
    inodes = collections.defaultdict(list)
    type_counts = collections.Counter()
    compression_counts = collections.Counter()

    while pos + 12 <= len(fs):
        if fs[pos:pos + 2] != JFFS_MAGIC:
            pos += 4
            continue
        magic, node_type, total, hdr_crc = struct.unpack_from("<HHII", fs, pos)
        if (
            total < 12 or total > 0x800000 or pos + total > len(fs)
            or jffs_crc(fs[pos:pos + 8]) != hdr_crc
        ):
            pos += 4
            continue
        type_counts[f"{node_type:04x}"] += 1
        if node_type == 0xE001 and total >= 40:
            pino, ver, ino, mctime, namelen, ftype, _pad, nodecrc, namecrc = (
                struct.unpack_from("<IIIIBBHII", fs, pos + 12)
            )
            name = bytes(fs[pos + 40:pos + 40 + namelen])
            if 40 + namelen <= total and jffs_crc(name) == namecrc:
                key = (pino, name)
                record = (ver, ino, ftype)
                if key not in directories or ver > directories[key][0]:
                    directories[key] = record
        elif node_type == 0xE002 and total >= 68:
            (ino, ver, mode, uid, gid, size, atime, mtime, ctime, offset,
             csize, dsize, comp, usercomp, flags, data_crc, node_crc) = (
                struct.unpack_from("<IIIHHIIIIIIIBBHII", fs, pos + 12)
            )
            compressed = bytes(fs[pos + 68:pos + 68 + csize])
            if (
                size <= MAX_FILE_SIZE and csize <= total - 68
                and jffs_crc(compressed) == data_crc
            ):
                compression_counts[str(comp)] += 1
                inodes[ino].append({
                    "version": ver, "mode": mode, "size": size,
                    "offset": offset, "compressed": comp,
                    "compressed_size": csize, "decompressed_size": dsize,
                    "data_position": base + pos + 68,
                })
        pos += (total + 3) & ~3

    children = collections.defaultdict(list)
    for (parent, name), (version, ino, ftype) in directories.items():
        if ino != 0:  # inode 0 is a deletion marker
            children[parent].append((name, ino))

    paths = {1: "/"}
    for _ in range(32):
        changed = False
        for parent, entries in children.items():
            if parent not in paths:
                continue
            for name, ino in entries:
                if ino in paths:
                    continue
                label = name.decode("utf-8", "replace")
                paths[ino] = paths[parent].rstrip("/") + "/" + label
                changed = True
        if not changed:
            break

    inventory = []
    for ino, path in sorted(paths.items(), key=lambda entry: entry[1]):
        nodes = inodes.get(ino, [])
        if nodes:
            newest = max(nodes, key=lambda n: n["version"])
            size, mode = newest["size"], newest["mode"]
            compression_ids = " ".join(str(v) for v in sorted({n["compressed"] for n in nodes}))
        else:
            size, mode, compression_ids = 0, 0, ""
        inventory.append({
            "path": path, "inode": ino, "mode": oct(mode),
            "size": size, "fragments": len(nodes), "compression": compression_ids,
        })

    summary = {
        "rootfs_offset": hex(base),
        "rootfs_length_requested": limit,
        "node_type_counts": dict(type_counts),
        "compression_counts": dict(compression_counts),
        "inventoried_paths": len(inventory),
        "inode_count": len(inodes),
    }
    return inventory, inodes, paths, summary


def extract_rootfs(image, inodes, paths, destination):
    """Extract payloads as regular files (symlinks never created)."""
    destination.mkdir(parents=True, exist_ok=True)
    exported = 0
    errors = []
    for ino, path in paths.items():
        nodes = inodes.get(ino, [])
        if not nodes or path == "/":
            continue
        newest = max(nodes, key=lambda n: n["version"])
        if not (stat.S_ISREG(newest["mode"]) or stat.S_ISLNK(newest["mode"])):
            continue
        parts = Path(path.lstrip("/")).parts
        if not parts or any(p in ("..", "", ".") or "\x00" in p for p in parts):
            errors.append(f"invalid path: {path!r}")
            continue
        size = newest["size"]
        data = bytearray(size)
        try:
            for node in sorted(nodes, key=lambda n: n["version"]):
                start = node["data_position"]
                compressed = image[start:start + node["compressed_size"]]
                if node["compressed"] == 0:
                    block = compressed
                elif node["compressed"] == 1:
                    block = bytes(node["decompressed_size"])
                elif node["compressed"] == 6:
                    block = zlib.decompress(compressed)
                else:
                    raise ValueError(f"unsupported compression {node['compressed']}")
                if len(block) != node["decompressed_size"]:
                    raise ValueError("fragment decompressed size mismatch")
                if node["offset"] < size:
                    write_n = min(len(block), size - node["offset"])
                    data[node["offset"]:node["offset"] + write_n] = block[:write_n]
            dest = destination.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            exported += 1
        except (ValueError, zlib.error, OSError) as exc:
            errors.append(f"{path}: {exc}")
    return {"exported_files": exported, "errors": errors}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", type=Path, help="local original firmware image (read only)")
    p.add_argument("--output", type=Path, help="write metadata.json and file_inventory.tsv")
    p.add_argument("--rootfs-offset", type=lambda x: int(x, 0), default=DEFAULT_ROOTFS_OFFSET)
    p.add_argument("--rootfs-length", type=lambda x: int(x, 0), default=DEFAULT_ROOTFS_LENGTH)
    p.add_argument("--extract-rootfs", action="store_true", help="extract vendor payloads locally; DO NOT publish them")
    args = p.parse_args(argv)
    if args.extract_rootfs and not args.output:
        p.error("--extract-rootfs requires --output")
    if args.rootfs_offset < 0 or args.rootfs_length <= 0:
        p.error("offset must be nonnegative and length positive")
    try:
        image = args.image.read_bytes()
    except OSError as exc:
        p.error(str(exc))

    inventory, inodes, paths, jffs = scan_jffs2(image, args.rootfs_offset, args.rootfs_length)
    metadata = {
        "image_name": args.image.name,
        "image_size": len(image),
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "uimage": inspect_uimage(image),
        "jffs2": jffs,
        "warning": "Static diagnostic result only; no board-level validation or safe flashing inference.",
    }
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        with (args.output / "file_inventory.tsv").open("w", encoding="utf-8") as fh:
            for row in inventory:
                fh.write("\t".join(str(row[k]) for k in (
                    "path", "inode", "mode", "size", "fragments", "compression"
                )) + "\n")
        if args.extract_rootfs:
            extraction = extract_rootfs(image, inodes, paths, args.output / "rootfs")
            print(json.dumps({"extraction": extraction}, indent=2), file=sys.stderr)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
