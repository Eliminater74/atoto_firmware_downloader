#!/usr/bin/env python3
# sdat2img.py — works with transfer.list v1–v4
# Correctly interprets the ranges header: first number = count of following integers.
# Defaults block_size to 4096 if header provides 0.

import sys

KNOWN_CMDS = {"new","zero","erase","move","stash","free","append","bsdiff","imgdiff"}

def to_int(s):
    try:
        return int(s)
    except:
        return None

def parse_ranges(s):
    # "4,0,3,10,11" -> [(0,3),(10,11)]
    toks = [t for t in s.replace(',', ' ').split() if t!='']
    if not toks:
        return []
    cnt = to_int(toks[0])
    nums = [to_int(x) for x in toks[1:]]
    if cnt is None or any(n is None for n in nums):
        raise ValueError("Bad ranges: non-integer token")
    if len(nums) != cnt:
        raise ValueError("Bad ranges length")
    if cnt % 2 != 0:
        raise ValueError("Bad ranges: odd number of integers")
    out = []
    for i in range(0, cnt, 2):
        start, end = nums[i], nums[i+1]
        if end < start:
            raise ValueError("Range end < start")
        out.append((start, end))
    return out

def parse_header(lines):
    L = [l.strip() for l in lines if l.strip()!='']
    if len(L) < 2:
        raise ValueError("transfer.list too short")
    version = to_int(L[0])
    if version not in (1,2,3,4):
        raise ValueError(f"Unsupported transfer.list version: {L[0]}")
    total_blocks = to_int(L[1])
    if total_blocks is None:
        raise ValueError("Bad total_blocks line")

    idx = 2
    block_size = 4096
    if version == 3:
        bs = to_int(L[idx]) if idx < len(L) else None
        if bs and bs > 0: block_size = bs
        idx += 1
    elif version == 4:
        # v4 adds stashed_blocks then block_size
        idx += 1  # stashed_blocks (ignored)
        bs = to_int(L[idx]) if idx < len(L) else None
        if bs and bs > 0: block_size = bs
        idx += 1

    # advance idx to first command-looking line
    while idx < len(L):
        tok = L[idx].split(' ',1)[0].lower()
        if tok in KNOWN_CMDS:
            break
        idx += 1

    return version, total_blocks, block_size, idx, L

def main():
    if len(sys.argv) != 4:
        print("Usage: python sdat2img.py <transfer.list> <new.dat> <out.img>")
        sys.exit(1)
    tlist, dat, outimg = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(tlist, 'r', errors='ignore') as f:
        version, total_blocks, block_size, idx, L = parse_header(f.readlines())

    print(f"transfer.list v{version}  blocks={total_blocks}  block_size={block_size}")

    commands = []
    for l in L[idx:]:
        if not l: continue
        if ' ' in l:
            c, a = l.split(' ', 1)
        else:
            c, a = l, ""
        commands.append((c.lower().strip(), a.strip()))

    with open(outimg, 'wb') as fout, open(dat, 'rb') as fdat:
        fout.truncate(total_blocks * block_size)

        for cmd, arg in commands:
            if cmd == 'new':
                for start, end in parse_ranges(arg):
                    length = (end - start) * block_size
                    if length <= 0: continue
                    data = fdat.read(length)
                    if len(data) != length:
                        raise EOFError("new.dat ended unexpectedly")
                    fout.seek(start * block_size)
                    fout.write(data)
            elif cmd in ('zero', 'erase'):
                # already zeroed by truncate
                continue
            else:
                # ignore incremental-only ops safely
                continue

    print(f"Done: wrote {outimg}")

if __name__ == "__main__":
    main()
