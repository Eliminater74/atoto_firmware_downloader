#!/usr/bin/env python3
# sdat2img.py — robust v1–v4 converter for *.new.dat + transfer.list
# Tolerant to weird range lines (bad counts / extra commas).
import sys

KNOWN_CMDS = {"new","zero","erase","move","stash","free","append","bsdiff","imgdiff"}

def try_int(s):
    try: return int(s)
    except: return None

def tokenize_ranges(s):
    # Turn "4,0,3,10,11" or "0, 3 , 10 , 11" or "0,3,10,11," into ints
    toks = []
    for t in s.replace(',', ' ').split():
        v = try_int(t)
        if v is not None: toks.append(v)
    return toks

def read_ranges_loose(s):
    toks = tokenize_ranges(s)
    if not toks: 
        return []
    # First try the canonical interpretation: first = count, rest are pairs.
    cnt = toks[0]
    nums = toks[1:]
    if len(nums) == cnt*2:
        pairs = [(nums[i], nums[i+1]) for i in range(0, len(nums), 2)]
        return pairs
    # Fall back #1: maybe the count is wrong; if even number of ints, pair them all.
    if len(toks) % 2 == 0:
        nums = toks
        return [(nums[i], nums[i+1]) for i in range(0, len(nums), 2)]
    # Fall back #2: drop the first token (bad count) and pair the rest if even.
    nums = toks[1:]
    if len(nums) % 2 == 0:
        return [(nums[i], nums[i+1]) for i in range(0, len(nums), 2)]
    # Last resort: ignore the last dangling number.
    nums = nums[:-1]
    if len(nums) % 2 == 0:
        return [(nums[i], nums[i+1]) for i in range(0, len(nums), 2)]
    raise ValueError("Unparseable ranges")

def parse_header(lines):
    L = [l.strip() for l in lines if l.strip()!='']
    if len(L) < 2:
        raise ValueError("transfer.list too short")
    version = try_int(L[0])
    if version not in (1,2,3,4):
        raise ValueError(f"Unsupported transfer.list version: {L[0]}")
    total_blocks = try_int(L[1])
    if total_blocks is None:
        raise ValueError("Bad total_blocks line")
    idx = 2
    if version in (1,2):
        block_size = 4096
    elif version == 3:
        block_size = try_int(L[idx]) or 4096
        idx += 1
    else:  # v4: version, total_blocks, stashed_blocks, block_size
        if idx < len(L): idx += 1  # stashed (ignored)
        block_size = 4096
        if idx < len(L):
            bs = try_int(L[idx])
            if bs and bs > 0: block_size = bs
            idx += 1
    # Advance idx until a command-looking line
    while idx < len(L):
        first = L[idx].split(' ',1)[0].lower()
        if first in KNOWN_CMDS: break
        if try_int(first) is not None: idx += 1; continue
        break
    return version, total_blocks, block_size, idx, L

def main():
    if len(sys.argv)!=4:
        print("Usage: python sdat2img.py <transfer.list> <new.dat> <out.img>")
        sys.exit(1)
    tlist, dat, outimg = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(tlist,'r',errors='ignore') as f:
        lines = f.readlines()
    version, total_blocks, block_size, idx, L = parse_header(lines)
    print(f"transfer.list v{version}  blocks={total_blocks}  block_size={block_size}")

    cmds=[]
    for l in L[idx:]:
        l=l.strip()
        if not l: continue
        if ' ' in l:
            c,a = l.split(' ',1)
        else:
            c,a = l, ""
        cmds.append((c.lower(), a))

    with open(outimg,'wb') as fout, open(dat,'rb') as fdat:
        fout.truncate(total_blocks*block_size)
        for cmd,arg in cmds:
            if cmd == 'new':
                ranges = read_ranges_loose(arg)
                for s,e in ranges:
                    length = (e - s) * block_size
                    if length <= 0: continue
                    data = fdat.read(length)
                    if len(data) != length:
                        raise EOFError("new.dat ended unexpectedly")
                    fout.seek(s*block_size)
                    fout.write(data)
            elif cmd in ('zero','erase'):
                continue
            else:
                # ignore incremental-only ops
                continue
    print(f"Done: wrote {outimg}")

if __name__ == "__main__":
    main()
