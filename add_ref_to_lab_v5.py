"""
PDF Label Reference Number Adder v5 (Name Verification Support)
Support for new CSV format and 3-step verification (PostOne -> Tracking -> Name).

Requirements:
    pip install pypdf reportlab --break-system-packages
"""

import sys
import re
import os
import csv
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
import tkinter as tk
from tkinter import filedialog

def normalize_text(text):
    """Clean text for comparison (remove spaces, lowercase)"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip().lower()

def check_name_presence(name_parts, page_text):
    """
    Check if parts of the name exist in the page text.
    Returns True if a significant part of the name is found.
    """
    if not name_parts or not page_text:
        return False
    
    page_text_norm = normalize_text(page_text)
    
    # Split full name into words (e.g., "Perna Cinzia Maria" -> ["perna", "cinzia", "maria"])
    # Filter out short words to avoid false positives on 'da', 'di', etc.
    parts = [p.lower() for p in name_parts.split() if len(p) > 2]
    
    if not parts:
        return False
        
    # Check if ALL significant name parts are in the text (strict)
    # OR at least the last name and first name are present.
    matches = 0
    for part in parts:
        if part in page_text_norm:
            matches += 1
            
    # If more than 50% of the name parts are found, we consider it a match
    return matches >= (len(parts) / 2)

def select_files_gui():
    """Open GUI dialogs to select PDF and CSV files"""
    print("\n🖱️  GUI MODE: Opening file selection dialogs...")
    
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # Select PDF
    print("\n📄 Step 1: Select PDF labels file...")
    pdf_path = filedialog.askopenfilename(
        title="Select PDF Labels File",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    
    if not pdf_path:
        print("❌ No PDF file selected. Cancelled.")
        return None
    print(f"✓ Selected PDF: {Path(pdf_path).name}")
    
    # Select CSV
    print("\n📊 Step 2: Select CSV mapping file...")
    csv_path = filedialog.askopenfilename(
        title="Select CSV Mapping File",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialdir=str(Path(pdf_path).parent)
    )
    
    if not csv_path:
        print("❌ No CSV file selected. Cancelled.")
        return None
    print(f"✓ Selected CSV: {Path(csv_path).name}")
    
    # Generate output filename
    pdf_folder = Path(pdf_path).parent
    pdf_name = Path(pdf_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = pdf_folder / f"{pdf_name}_labeled_{timestamp}.pdf"
    
    root.destroy()
    return str(pdf_path), str(csv_path), str(output_path)

def create_reference_overlay(reference_number, page_width, page_height):
    """Create a PDF overlay with reference number at bottom-left"""
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Position: bottom-left corner
    x = 200
    y = 3
    can.setFont("Helvetica-Bold", 10)
    text = f"REF: {reference_number}"
    can.drawString(x, y, text)
    
    can.save()
    packet.seek(0)
    return packet

def extract_postone_number_from_page(text):
    """Extract PostOne number (R or P + 10 digits)"""
    try:
        match = re.search(r'[RP]\d{10}', text)
        return match.group(0) if match else None
    except:
        return None

def extract_tracking_from_page(text):
    """Extract potential tracking numbers"""
    try:
        # Looking for long alphanumeric strings (common in tracking)
        # Excluding the R/P numbers found above
        matches = re.findall(r'(?<![RP])([A-Z0-9]{12,})', text)
        return matches if matches else []
    except:
        return []

def process_labels(input_pdf_path, mapping_csv_path, output_pdf_path):
    print("\n" + "="*60)
    print("📖 STEP 1: Reading mapping CSV (New Format)")
    print("="*60)
    
    # Data storage
    db_by_postone = {} # Key: R-Number -> Value: {ref, name}
    db_by_tracking = {} # Key: Tracking -> Value: {ref, name}
    db_by_name = {}     # Key: Full Name -> Value: {ref, name} (For fallback)
    
    try:
        # Try different encodings for CSV
        encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'latin-1']
        rows_loaded = 0
        
        for encoding in encodings:
            try:
                with open(mapping_csv_path, 'r', encoding=encoding, newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader, None) # Skip header
                    
                    if not header: continue
                    
                    # Reset dicts for new attempt
                    db_by_postone = {}
                    db_by_tracking = {}
                    
                    for row in reader:
                        if len(row) < 7: continue # Ensure enough columns
                        
                        # Indices based on "Shipments-Гриин Деливери" file:
                        # 0: Номер на пратка (R...)
                        # 1: Проследяващ номер (Tracking)
                        # 2: Номер по референция (Reference)
                        # 6: Име на получател (Name)
                        
                        p_number = row[0].strip()
                        tracking = row[1].strip()
                        ref_num = row[2].strip()
                        client_name = row[6].strip()
                        
                        data_pack = {'ref': ref_num, 'name': client_name}
                        
                        if p_number:
                            db_by_postone[p_number] = data_pack
                        if tracking:
                            db_by_tracking[tracking] = data_pack
                        if client_name:
                            db_by_name[normalize_text(client_name)] = data_pack
                            
                    if len(db_by_postone) > 0:
                        print(f"✓ Successfully read CSV with encoding: {encoding}")
                        rows_loaded = len(db_by_postone)
                        break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"⚠️ Error with encoding {encoding}: {e}")
                continue

        if rows_loaded == 0:
            print("❌ Could not read any valid data from CSV.")
            return False
            
        print(f"✓ Loaded {rows_loaded} orders.")
        
    except Exception as e:
        print(f"❌ Critical error reading CSV: {e}")
        return False

    print("\n" + "="*60)
    print("🔨 STEP 2: Processing PDF Labels")
    print("="*60)
    
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)
    
    stats = {
        'postone': 0,
        'tracking': 0,
        'name_search': 0,
        'unmatched': 0,
        'verified': 0,
        'verification_failed': 0
    }
    
    for i, page in enumerate(reader.pages):
        page_num = i + 1
        page_text = page.extract_text()
        
        print(f"\n📄 Page {page_num}/{total_pages}:")
        
        found_ref = None
        found_data = None # Will hold {'ref':..., 'name':...}
        method = None
        
        # --- 1. SEARCH BY POSTONE (R/P Number) ---
        p_num = extract_postone_number_from_page(page_text)
        if p_num and p_num in db_by_postone:
            found_data = db_by_postone[p_num]
            method = "PostOne ID"
            stats['postone'] += 1
        
        # --- 2. SEARCH BY TRACKING (Fallback) ---
        if not found_data:
            track_nums = extract_tracking_from_page(page_text)
            for t in track_nums:
                if t in db_by_tracking:
                    found_data = db_by_tracking[t]
                    method = "Tracking"
                    stats['tracking'] += 1
                    break
        
        # --- 3. SEARCH BY NAME (Deep Fallback) ---
        # If ID/Tracking failed, try to find the client name in the text
        if not found_data:
            page_text_norm = normalize_text(page_text)
            for name_key, data in db_by_name.items():
                # We check if the csv name exists in the page text
                if name_key in page_text_norm and len(name_key) > 5:
                    found_data = data
                    method = "Client Name Search"
                    stats['name_search'] += 1
                    break

        # --- PROCESS RESULT & VERIFY ---
        if found_data:
            ref = found_data['ref']
            expected_name = found_data['name']
            
            # Perform Name Verification (Step 3 from requirements)
            is_verified = check_name_presence(expected_name, page_text)
            
            status_icon = "✅" if is_verified else "⚠️"
            verify_msg = f"Name matched: '{expected_name}'" if is_verified else f"NAME MISMATCH? Exp: '{expected_name}'"
            
            if is_verified:
                stats['verified'] += 1
            else:
                stats['verification_failed'] += 1
            
            print(f"   {status_icon} Found via {method}: {p_num if p_num else 'N/A'}")
            print(f"   -> REF: {ref}")
            print(f"   -> Verification: {verify_msg}")
            
            # Apply Stamp
            try:
                overlay = create_reference_overlay(ref, float(page.mediabox.width), float(page.mediabox.height))
                page.merge_page(PdfReader(overlay).pages[0])
            except Exception as e:
                print(f"   ❌ Error stamping PDF: {e}")
                
        else:
            print("   ❌ NO MATCH FOUND.")
            print(f"      (Ids found: {p_num}, Tracking found: {extract_tracking_from_page(page_text)})")
            stats['unmatched'] += 1
            
        writer.add_page(page)

    # Save Output
    print("\n" + "="*60)
    print("💾 STEP 3: Saving Output")
    print("="*60)
    
    with open(output_pdf_path, 'wb') as f:
        writer.write(f)
        
    # Final Report
    print(f"\n📊 SUMMARY REPORT:")
    print(f"   Total Pages: {total_pages}")
    print(f"   Matched by PostOne (R/P): {stats['postone']}")
    print(f"   Matched by Tracking:      {stats['tracking']}")
    print(f"   Matched by Name Search:   {stats['name_search']}")
    print(f"   -------------------------")
    print(f"   ✅ Name Verification Passed: {stats['verified']}")
    print(f"   ⚠️ Name Verification Warning: {stats['verification_failed']}")
    print(f"   ❌ Unmatched Pages:          {stats['unmatched']}")
    print(f"\n   File saved to: {output_pdf_path}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) == 4:
        process_labels(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        result = select_files_gui()
        if result:
            process_labels(*result)
