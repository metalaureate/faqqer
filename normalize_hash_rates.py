#!/usr/bin/env python3
"""
Normalize Hash Rate Data
Converts all hash rate values to consistent units and outputs clean CSV
"""

import re
import csv
from datetime import datetime

INPUT_FILE = "hash_rate_history.txt"
OUTPUT_FILE = "normalized_hash_rates.csv"

def parse_hash_value(value_str):
    """
    Parse a hash rate string and convert to base units
    Returns value in base unit (H/s for hashes, g/s for graphs)
    
    Examples:
        "250 MH" -> 250000000 (250 million H/s)
        "3.70 GH" -> 3700000000 (3.7 billion H/s)
        "47.0 TH" -> 47000000000000 (47 trillion H/s)
        "120 Kg" -> 120000 (120 thousand g/s)
    """
    if not value_str or value_str == 'N/A':
        return None
    
    # Clean up the string
    value_str = value_str.strip()
    
    # Handle special cases like "kgraphs"
    value_str = value_str.replace('kgraphs', 'Kg')
    
    # Extract number and unit
    match = re.match(r'([\d.]+)\s*([A-Za-z/]+)', value_str)
    if not match:
        return None
    
    number = float(match.group(1))
    unit = match.group(2)
    
    # Define multipliers for hash units (H, MH, GH, TH, etc.)
    hash_multipliers = {
        'H': 1,
        'kH': 1e3,
        'KH': 1e3,
        'MH': 1e6,
        'GH': 1e9,
        'TH': 1e12,
        'PH': 1e15,
        'EH': 1e18
    }
    
    # Define multipliers for graph units (g, Kg, Mg, etc.)
    graph_multipliers = {
        'g': 1,
        'kg': 1e3,
        'Kg': 1e3,
        'KG': 1e3,
        'Mg': 1e6,
        'MG': 1e6,
        'Gg': 1e9,
        'GG': 1e9
    }
    
    # Remove /s suffix if present
    unit_clean = unit.replace('/s', '')
    
    # Try hash units first
    if unit_clean in hash_multipliers:
        return number * hash_multipliers[unit_clean]
    
    # Try graph units
    if unit_clean in graph_multipliers:
        return number * graph_multipliers[unit_clean]
    
    print(f"Warning: Unknown unit '{unit}' in value '{value_str}'")
    return None

def convert_to_display_unit(value, unit_type='hash'):
    """
    Convert base value to appropriate display unit
    
    unit_type: 'hash' for H/s units, 'graph' for g/s units
    Returns: tuple (value, unit_string)
    """
    if value is None:
        return None, None
    
    if unit_type == 'hash':
        # Convert to TH/s (terahashes per second)
        return value / 1e12, 'TH'
    elif unit_type == 'graph':
        # Convert to Kg/s (kilographs per second)
        return value / 1e3, 'Kg'
    
    return value, ''

def parse_entry(text):
    """
    Parse a single hash rate entry and extract all fields
    """
    # Extract date
    date_match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
    if not date_match:
        return None
    
    date_str = date_match.group(1)
    
    # Extract block height
    block_match = re.search(r'Block Height:\s*([\d,]+)', text)
    block_height = block_match.group(1).replace(',', '') if block_match else None
    
    # Extract SHA3x or SHA3 Hash Rate
    sha_match = re.search(r'SHA3(?:x)?(?: Hash Rate)?:\s*([\d.]+\s*[A-Za-z/]+)', text)
    sha_value = parse_hash_value(sha_match.group(1)) if sha_match else None
    
    # Extract RandomX (Tari) - could be labeled as "RandomX (Tari)" or "RandomX (Tari) Hash Rate"
    rxt_match = re.search(r'RandomX \(Tari\)(?: Hash Rate)?:\s*([\d.]+\s*[A-Za-z/]+)', text)
    rxt_value = parse_hash_value(rxt_match.group(1)) if rxt_match else None
    
    # Extract RandomX (Merged-Mined XMR) - could have various labels
    rxm_match = re.search(r'RandomX \(Merged-Mined XMR\)(?: Hash Rate)?:\s*([\d.]+\s*[A-Za-z/]+)', text)
    rxm_value = parse_hash_value(rxm_match.group(1)) if rxm_match else None
    
    # Early format (May 2025): just "RandomX Hash Rate" without Tari/XMR distinction
    # Initially only SHA3 and RXM (merged-mined XMR) existed, RXT (Tari) came later
    if not rxt_match and not rxm_match:
        early_rx_match = re.search(r'RandomX Hash Rate:\s*([\d.]+\s*[A-Za-z/]+)', text)
        if early_rx_match:
            # In early format, this was the merged-mined XMR RandomX value
            rxm_value = parse_hash_value(early_rx_match.group(1))
            rxt_value = None  # Tari RandomX wasn't tracked separately yet
    
    # Extract Cuckaroo 29
    c29_match = re.search(r'Cuckaroo 29:\s*([\d.]+\s*[A-Za-z/]+)', text)
    c29_value = parse_hash_value(c29_match.group(1)) if c29_match else None
    
    # Convert to display units
    rxt_display, _ = convert_to_display_unit(rxt_value, 'hash') if rxt_value else (None, None)
    rxm_display, _ = convert_to_display_unit(rxm_value, 'hash') if rxm_value else (None, None)
    sha_display, _ = convert_to_display_unit(sha_value, 'hash') if sha_value else (None, None)
    c29_display, _ = convert_to_display_unit(c29_value, 'graph') if c29_value else (None, None)
    
    return {
        'date': date_str,
        'block_height': block_height,
        'net_sha3_th': round(sha_display, 2) if sha_display else None,
        'net_rxt_gh': round(rxt_display * 1000, 2) if rxt_display else None,  # TH to GH
        'net_rxm_gh': round(rxm_display * 1000, 2) if rxm_display else None,  # TH to GH
        'net_c29_kg': round(c29_display, 2) if c29_display else None
    }

def main():
    print("Reading hash rate history...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the separator lines
    entries = content.split('='*80)
    
    parsed_data = []
    
    for entry in entries:
        if 'Date:' in entry and 'Block Height:' in entry:
            parsed = parse_entry(entry)
            if parsed:
                parsed_data.append(parsed)
    
    print(f"Parsed {len(parsed_data)} entries")
    
    # Sort by date
    parsed_data.sort(key=lambda x: x['date'])
    
    # Write to CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['date', 'block_height', 'net_sha3_th', 'net_rxt_gh', 'net_rxm_gh', 'net_c29_kg']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header with units
        f.write('Date,Block Height,net_sha3 (TH/s),net_rxt (GH/s),net_rxm (GH/s),net_c29 (Kg/s)\n')
        
        for row in parsed_data:
            # Format None values as empty strings
            formatted_row = {
                'date': row['date'],
                'block_height': row['block_height'] if row['block_height'] else '',
                'net_sha3_th': row['net_sha3_th'] if row['net_sha3_th'] is not None else '',
                'net_rxt_gh': row['net_rxt_gh'] if row['net_rxt_gh'] is not None else '',
                'net_rxm_gh': row['net_rxm_gh'] if row['net_rxm_gh'] is not None else '',
                'net_c29_kg': row['net_c29_kg'] if row['net_c29_kg'] is not None else ''
            }
            writer.writerow(formatted_row)
    
    print(f"\n✅ Normalized data written to: {OUTPUT_FILE}")
    print(f"\nColumn headers:")
    print(f"  Date             - Timestamp of measurement")
    print(f"  Block Height     - Blockchain block number")
    print(f"  net_sha3 (TH/s)  - SHA3x hash rate in terahashes per second")
    print(f"  net_rxt (GH/s)   - RandomX (Tari) hash rate in gigahashes per second")
    print(f"  net_rxm (GH/s)   - RandomX (Merged-Mined XMR) in gigahashes per second")
    print(f"  net_c29 (Kg/s)   - Cuckaroo 29 in kilographs per second")
    
    # Show first few rows as sample
    print(f"\nFirst 5 rows:")
    print("-" * 100)
    with open(OUTPUT_FILE, 'r') as f:
        for i, line in enumerate(f):
            if i < 6:  # Header + 5 rows
                print(line.rstrip())
            else:
                break
    
    print(f"\nLast 5 rows:")
    print("-" * 100)
    with open(OUTPUT_FILE, 'r') as f:
        lines = f.readlines()
        for line in lines[-5:]:
            print(line.rstrip())

if __name__ == "__main__":
    main()
