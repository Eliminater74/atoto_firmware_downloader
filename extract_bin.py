import zipfile
import os
import sys
import re
import itertools
import zlib

def get_strings(filename, min_len=4):
    try:
        with open(filename, 'rb') as f:
            content = f.read()
            # Only matching alphanumeric and common symbols for passwords
            regex = b'[a-zA-Z0-9._@-]{' + str(min_len).encode() + b',}'
            return [s.decode('utf-8') for s in re.findall(regex, content)]
    except Exception as e:
        print(f"Could not read {filename}: {e}")
        return []

def extract_bin(file_path, output_dir):
    parent_dir = os.path.dirname(file_path)
    
    # 1. Base Candidates
    base_passwords = [
        'atoto', 'Atoto', 'ATOTO', 
        'Topway', 'topway', 
        'admin', 'password', 'root',
        '6315', 'S8G2A7PE',
        '20250401', '20250514', 
        'developer', 'autochips', 'fyt', 'syu'
        '18498882', # file size of one entry
        'APP20250514', 'SYSTEM20250401'
    ]
    
    print("Scraping strings from sibling files...")
    scraped_strings = set()
    for f in os.listdir(parent_dir):
        full_path = os.path.join(parent_dir, f)
        if os.path.isfile(full_path) and full_path != file_path and not f.endswith('.zip') and not f.endswith('.py'):
            print(f"  Scraping {f}...")
            strings = get_strings(full_path)
            for s in strings:
                s = s.strip()
                if 4 <= len(s) <= 20: 
                    scraped_strings.add(s)
    
    print(f"Found {len(scraped_strings)} unique strings.")
    
    candidates = list(base_passwords) + list(scraped_strings)
    
    # Deduplicate
    seen = set()
    final_candidates = []
    
    # Priority Candidates from lsec6315update
    lsec_candidates = [
        'JC!6zTq3', ':q0C\'$', 'D&rM*v0&',
        'sql6315update', 'mcuall6315.bin', 'lsec6315update',
        'AT-CZ1', 'APPUHDR5', 'AT-KC0',
        '1efd3c03f55d4a16cd1fc9d72fe0ccdc',
        'cfb63512857096bf661eda2c894ccc2f',
        '3c6f402e86dc8e952742ab74e99ab299',
        'f2a9fc1625270fa32e6c4606fb28d170',
        '299c25e9635a8644969fadd6fd795744',
        '75796bf6d98c61cf2ccbc74e0cec9dd0',
        'b03272f867bc814d6cf7c8e8b9b35f9e',
        '3c6e0b8a9c15224a8228b9a98ca1531d',
        'a2e1781b3d206d5634cc3539227daf50',
        '8be3966471b27a3640e049f3dd6bcb32',
        '6d7e0727db8d5723067c6c864c317e33',
        '98e01e927340688714be6631c773d527',
        '1703ee7c9c9877531b89a7ce16f3e627',
        '048a02243bb74474b25233bda3cd02f8',
        '0cbf702ad64585d8bcd8ced56b2580c6',
        '3f3387d789c0d7d3ab55938755ece6e6',
        '0123456789abcdef', '0123456789ABCDEF'
    ]
    
    for c in lsec_candidates:
        if c not in seen:
            final_candidates.append(c.encode('utf-8'))
            seen.add(c)

    for c in candidates:
        if c not in seen:
            final_candidates.append(c.encode('utf-8'))
            seen.add(c)
    
    # Skip expanded brute force for now to test these quickly
    # Expanded Brute Force
    print("Skipping expanded brute force for targeted check...")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Extracting {file_path} to {output_dir}...")
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Try without password
            try:
                zip_ref.testzip()
                print("No password needed or password is empty.")
                zip_ref.extractall(output_dir)
                return
            except (RuntimeError, zipfile.BadZipFile):
                print("Encrypted. Starting cracking...")

            # Target the small file 'Ver'
            target_file = 'Ver'
            if target_file not in zip_ref.namelist():
                print(f"Warning: {target_file} not found, finding any small encrypted file...")
                for info in zip_ref.infolist():
                    if info.flag_bits & 0x1 and info.file_size > 0:
                        target_file = info.filename
                        break
            
            print(f"Targeting file: {target_file}")
            total = len(final_candidates)
            
            for idx, pwd in enumerate(final_candidates):
                if idx % 1000 == 0:
                    print(f"Progress: {idx}/{total}...")
                try:
                    # Robust check: Read ENTIRE file to force CRC check
                    with zip_ref.open(target_file, 'r', pwd=pwd) as f:
                        f.read()
                    
                    print(f"\nSUCCESS! Password found: {pwd.decode()}")
                    print("Extracting all files...")
                    zip_ref.extractall(output_dir, pwd=pwd)
                    print("Full extraction complete.")
                    return
                except (RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error):
                    continue
            
            print("Failed to find password in smart list.")
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    file_path = r"i:\GITHUB\ATOTO_Firmware\atoto_firmware_downloader\ATOTO_Firmware\S8G2A7PE\S8G2A7PE_6315-_6315-SYSTEM20250401-APP20250514\6315-SYSTEM20250401-APP20250514\AllAppUpdate.bin"
    output_dir = os.path.join(os.path.dirname(file_path), "AllAppUpdate_extracted")
    extract_bin(file_path, output_dir)
