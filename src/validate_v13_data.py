# -*- coding: utf-8 -*-
"""
V13 DATA VALIDATION
===================
Comprehensive validation for 1120 clean questions before fine-tuning
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# Paths
project_dir = Path(__file__).parent.parent
input_file = project_dir / "data" / "last_clean_data_merged" / "merged_questions_converted.jsonl"
output_dir = project_dir / "data" / "v13_final"

# Word count rules (from RAG V3)
WORD_COUNT_RULES = {
    "Paragraf": {"min": 80, "max": 220},
    "Cümlede Anlam": {"min": 60, "max": 180},
    "Sözcükte Anlam": {"min": 60, "max": 180},
    "Yazım Kuralları": {"min": 60, "max": 180},
    "Dil Bilgisi": {"min": 60, "max": 180},
    "default": {"min": 60, "max": 220}
}

def count_words(text):
    """Count words in Turkish text"""
    return len(text.split())

def extract_konu_alt_konu(user_field):
    """Extract konu and alt_konu from user field"""
    konu = None
    alt_konu = None
    
    if "Konu:" in user_field:
        konu = user_field.split("Konu:")[1].split("\n")[0].strip()
    
    if "Alt Konu:" in user_field:
        alt_konu = user_field.split("Alt Konu:")[1].split("\n")[0].strip()
    
    return konu, alt_konu

def validate_item(item, index):
    """Validate a single data item"""
    errors = []
    warnings = []
    
    # Check required fields
    if "user" not in item:
        errors.append(f"Missing 'user' field")
        return errors, warnings, None
    
    if "assistant" not in item:
        errors.append(f"Missing 'assistant' field")
        return errors, warnings, None
    
    # Parse assistant JSON
    try:
        assistant_data = json.loads(item["assistant"])
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in 'assistant': {e}")
        return errors, warnings, None
    
    # Check required fields in assistant
    required_fields = ["metin", "soru", "sik_a", "sik_b", "sik_c", "sik_d", "dogru_cevap"]
    for field in required_fields:
        if field not in assistant_data:
            errors.append(f"Missing '{field}' in assistant JSON")
        elif not assistant_data[field]:
            warnings.append(f"Empty '{field}' in assistant JSON")
    
    if errors:
        return errors, warnings, None
    
    # Validate dogru_cevap
    if assistant_data["dogru_cevap"] not in ["A", "B", "C", "D"]:
        errors.append(f"Invalid dogru_cevap: {assistant_data['dogru_cevap']}")
    
    # Extract konu and alt_konu
    konu, alt_konu = extract_konu_alt_konu(item["user"])
    
    if not konu:
        warnings.append("Could not extract 'konu' from user field")
    if not alt_konu:
        warnings.append("Could not extract 'alt_konu' from user field")
    
    # Word count validation
    metin_word_count = count_words(assistant_data["metin"])
    
    # Get rule for this konu
    rule = WORD_COUNT_RULES.get(konu, WORD_COUNT_RULES["default"])
    
    if metin_word_count < rule["min"]:
        warnings.append(f"Word count too low: {metin_word_count} < {rule['min']} (konu: {konu})")
    elif metin_word_count > rule["max"]:
        warnings.append(f"Word count too high: {metin_word_count} > {rule['max']} (konu: {konu})")
    
    # Metadata
    metadata = {
        "konu": konu,
        "alt_konu": alt_konu,
        "word_count": metin_word_count,
        "index": index
    }
    
    return errors, warnings, metadata

def main():
    print("=" * 70)
    print("V13 DATA VALIDATION")
    print("=" * 70)
    print()
    
    # Load data
    print(f"📂 Loading: {input_file}")
    data = []
    load_errors = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                item = json.loads(line)
                data.append(item)
            except json.JSONDecodeError as e:
                print(f"   ❌ Line {i}: JSON decode error: {e}")
                load_errors += 1
    
    print(f"✅ Loaded: {len(data)} items")
    if load_errors:
        print(f"⚠️  Load errors: {load_errors}")
    print()
    
    # Validate each item
    print("🔍 Validating items...")
    print()
    
    all_errors = []
    all_warnings = []
    valid_items = []
    metadata_list = []
    
    for i, item in enumerate(data):
        errors, warnings, metadata = validate_item(item, i)
        
        if errors:
            all_errors.append((i, errors))
            print(f"❌ Item {i}:")
            for error in errors:
                print(f"   - {error}")
        else:
            valid_items.append(item)
            metadata_list.append(metadata)
            
            if warnings:
                all_warnings.append((i, warnings))
    
    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total items:        {len(data)}")
    print(f"Valid items:        {len(valid_items)}")
    print(f"Items with errors:  {len(all_errors)}")
    print(f"Items with warnings: {len(all_warnings)}")
    print()
    
    # Distribution analysis
    if metadata_list:
        print("=" * 70)
        print("DISTRIBUTION ANALYSIS")
        print("=" * 70)
        print()
        
        konu_dist = Counter([m["konu"] for m in metadata_list if m["konu"]])
        alt_konu_dist = Counter([m["alt_konu"] for m in metadata_list if m["alt_konu"]])
        
        print("📊 KONU DISTRIBUTION:")
        for konu, count in konu_dist.most_common():
            print(f"   {konu:30s}: {count:4d}")
        print()
        
        print("📊 TOP 15 ALT KONU:")
        for alt_konu, count in alt_konu_dist.most_common(15):
            print(f"   {alt_konu:30s}: {count:4d}")
        print()
        
        # Word count analysis
        word_counts = [m["word_count"] for m in metadata_list]
        print("📊 WORD COUNT STATISTICS:")
        print(f"   Min:      {min(word_counts)}")
        print(f"   Max:      {max(word_counts)}")
        print(f"   Average:  {sum(word_counts) / len(word_counts):.1f}")
        print(f"   Median:   {sorted(word_counts)[len(word_counts)//2]}")
        print()
        
        # Word count distribution
        bins = [0, 60, 80, 120, 180, 220, 10000]
        bin_labels = ["<60", "60-80", "80-120", "120-180", "180-220", ">220"]
        bin_counts = [0] * len(bin_labels)
        
        for wc in word_counts:
            for i in range(len(bins) - 1):
                if bins[i] <= wc < bins[i+1]:
                    bin_counts[i] += 1
                    break
        
        print("📊 WORD COUNT DISTRIBUTION:")
        for label, count in zip(bin_labels, bin_counts):
            pct = count / len(word_counts) * 100
            print(f"   {label:12s}: {count:4d} ({pct:5.1f}%)")
        print()
    
    # Show warnings summary
    if all_warnings:
        print("=" * 70)
        print("WARNINGS SUMMARY")
        print("=" * 70)
        
        warning_types = Counter()
        for i, warnings in all_warnings:
            for warning in warnings:
                # Extract warning type
                if "Word count too low" in warning:
                    warning_types["Word count too low"] += 1
                elif "Word count too high" in warning:
                    warning_types["Word count too high"] += 1
                else:
                    warning_types[warning] += 1
        
        for warning_type, count in warning_types.most_common():
            print(f"   {warning_type:40s}: {count:4d}")
        print()
    
    # Save valid data for next step
    if valid_items:
        output_dir.mkdir(parents=True, exist_ok=True)
        valid_file = output_dir / "valid_data.jsonl"
        
        with open(valid_file, 'w', encoding='utf-8') as f:
            for item in valid_items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print("=" * 70)
        print(f"✅ Saved {len(valid_items)} valid items to:")
        print(f"   {valid_file}")
        print("=" * 70)
    
    # Return status code
    if all_errors:
        print("\n⚠️  Validation completed with errors!")
        return 1
    elif all_warnings:
        print("\n✅ Validation completed with warnings only.")
        return 0
    else:
        print("\n✅ Validation completed successfully!")
        return 0

if __name__ == "__main__":
    exit(main())
