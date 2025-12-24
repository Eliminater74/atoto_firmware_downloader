import zipfile
import sys

def analyze_zip(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            print(f"Analyzing {file_path}...")
            encrypted_count = 0
            
            # Find candidate for testing
            best_candidate = None
            min_size = float('inf')
            
            print(f"{'Filename':<50} | {'Size':<10} | {'Encrypted':<10}")
            print("-" * 80)
            
            for info in zip_ref.infolist():
                is_encrypted = info.flag_bits & 0x1
                status = "YES" if is_encrypted else "NO"
                if is_encrypted:
                    encrypted_count += 1
                    # We want a small file but not empty
                    if 10 < info.file_size < min_size:
                        min_size = info.file_size
                        best_candidate = info.filename
                
                if encrypted_count < 10:
                    print(f"{info.filename[:47]:<50} | {info.file_size:<10} | {status:<10}")
            
            print("-" * 80)
            print(f"Total files: {len(zip_ref.infolist())}")
            print(f"Encrypted files: {encrypted_count}")
            print(f"Best candidate for cracking: {best_candidate} (Size: {min_size})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    file_path = r"i:\GITHUB\ATOTO_Firmware\atoto_firmware_downloader\ATOTO_Firmware\S8G2A7PE\S8G2A7PE_6315-_6315-SYSTEM20250401-APP20250514\6315-SYSTEM20250401-APP20250514\AllAppUpdate.bin"
    analyze_zip(file_path)
