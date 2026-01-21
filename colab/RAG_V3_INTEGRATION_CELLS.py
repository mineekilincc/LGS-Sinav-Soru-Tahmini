# RAG V3 Integration - Colab Implementation Code
# Copy-paste these cells into your notebook

## ========================================
## NEW CELL 1: Install Dependencies
## ========================================

!pip install -q pyyaml==6.0

print("✅ PyYAML kuruldu!")


## ========================================
## NEW CELL 2: RAG V3 Setup & Load
## ========================================

import sys
import yaml
from pathlib import Path

# RAG system path (DRIVE'DAKI YOLUMUZU GÜNCELLE!)
RAG_SYSTEM_PATH = '/content/drive/MyDrive/LGS_Training/rag_system'
sys.path.insert(0, RAG_SYSTEM_PATH)

# Import RAG V3
from rag_v3 import RAGSystemV3

# Initialize
project_root = Path(RAG_SYSTEM_PATH)
rag = RAGSystemV3(project_root)

print("\n✅ RAG V3 Successfully Loaded!")
print(f"   📄 RAG Docs: {len(rag.rag_docs)} documents")
print(f"   📋 Rules: {len(rag.rules)} rule sets")


## ========================================
## NEW CELL 3: Test RAG System
## ========================================

# Test RAG doc retrieval
print("="*70)
print("RAG V3 SYSTEM TEST")
print("="*70)

# Test 1: Get RAG doc
doc = rag.get_rag_doc_for_topic("Paragraf")
print(f"\n📄 Paragraf RAG Doc: {len(doc)} characters")
print(f"   Preview: {doc[:200]}...")

# Test 2: Get rule
rule = rag.get_rule_for_question_type("Paragraf", "Ana Düşünce")
print(f"\n📋 Ana Düşünce Rules:")
print(f"   Min words: {rule['min_words']}")
print(f"   Max words: {rule['max_words']}")
print(f"   Text required: {rule['text_required']}")
print(f"   Allowed questions: {len(rule['allowed_question_roots'])}")

# Test 3: Build full prompt
prompt = rag.build_full_prompt("Paragraf", "Ana Düşünce")
print(f"\n🎯 Full Prompt Length: {len(prompt)} characters")
print(f"   Preview: {prompt[:300]}...")

print("\n✅ RAG V3 çalışıyor!")


## ========================================
## NEW CELL 4: Enhanced Prompt Builder
## ========================================

def build_enhanced_system_prompt(konu, alt_konu, rag_system):
    """
    RAG V3 ile enhanced system prompt oluştur
    
    Returns complete system prompt with:
    - General strategy
    - Topic-specific strategic knowledge
    - Strict rules for question type
    """
    # Get components
    general_strategy = rag_system.get_general_strategy()
    rag_doc = rag_system.get_rag_doc_for_topic(konu)
    rule = rag_system.get_rule_for_question_type(konu, alt_konu)
    
    # Build system prompt
    system_prompt = f"""# LGS TÜRKÇE SORU ÜRETME SİSTEMİ

## GENEL STRATEJİ
{general_strategy[:500] if general_strategy else 'Genel kurallara uy.'}...

## KONU-SPECIFIC STRATEJİK BİLGİ
{rag_doc[:800] if rag_doc else 'Genel kurallara uy.'}...

## KESİN KURALLAR
Soru Tipi: **{konu} - {alt_konu}**
"""
    
    if rule:
        system_prompt += f"""
### Format Gereksinimleri:
- **Minimum Kelime**: {rule['min_words']}
- **Maximum Kelime**: {rule['max_words']}
- **Metin Gerekli**: {'✅ Evet' if rule['text_required'] else '❌ Hayır'}
- **Highlight Gerekli**: {'✅ Evet' if rule.get('highlight_required', False) else '❌ Hayır'}
- **Numaralı Cümleler**: {'✅ Evet (' + str(rule.get('sentence_count', 4)) + ' cümle)' if rule.get('numbered_sentences', False) else '❌ Hayır'}

### İzin Verilen Soru Kalıpları:
"""
        for i, q in enumerate(rule.get('allowed_question_roots', []), 1):
            system_prompt += f"{i}. {q}\n"
    
    system_prompt += """

## ÇIKTI FORMATI
Sadece JSON döndür, açıklama yapma:
{
  "metin": "...",
  "soru": "...",
  "sik_a": "...",
  "sik_b": "...",
  "sik_c": "...",
  "sik_d": "...",
  "dogru_cevap": "A/B/C/D"
}

DİKKAT: Kuralları TAM olarak takip et!
"""
    
    return system_prompt

print("✅ Enhanced prompt builder hazır!")


## ========================================
## NEW CELL 5: RAG-Enhanced Generation
## ========================================

def generate_question_with_rag(
    konu, 
    alt_konu, 
    rag_system,
    model,
    tokenizer,
    max_new_tokens=1200,
    temperature=0.7,
    top_p=0.9
):
    """
    RAG V3 ile enhanced soru üretimi
    """
    # Build enhanced system prompt
    system_prompt = build_enhanced_system_prompt(konu, alt_konu, rag_system)
    
    # Simple user prompt
    user_prompt = f"Konu: {konu}\nAlt Konu: {alt_konu}\n\nBu kriterlere göre LGS Türkçe sorusu üret."
    
    # Combine messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract assistant response
    if "assistant" in response:
        response = response.split("assistant")[-1].strip()
    
    # Extract JSON
    if "{" in response and "}" in response:
        start = response.index("{")
        end = response.rindex("}") + 1
        response = response[start:end]
    
    return response

print("✅ RAG-enhanced generation function hazır!")


## ========================================
## NEW CELL 6: RAG vs Non-RAG Comparison Test
## ========================================

# Test cases
test_cases = [
    ("Paragraf", "Ana Düşünce"),
    ("Cümlede Anlam", "Sebep-Sonuç"),
    ("Sözcükte Anlam", "Çok Anlamlılık"),
]

print("="*70)
print("RAG V3 vs NON-RAG COMPARISON")
print("="*70)

for konu, alt_konu in test_cases:
    print(f"\n### {konu} - {alt_konu}")
    print("-"*70)
    
    # Get rule for comparison
    rule = rag.get_rule_for_question_type(konu, alt_konu)
    if rule:
        print(f"Expected: {rule['min_words']}-{rule['max_words']} words")
    
    # Without RAG (original function)
    print("\n📄 WITHOUT RAG:")
    result_basic = generate_question(konu, alt_konu)
    valid, msg, data = validate_question(result_basic)
    print(f"  Status: {msg}")
    if data:
        wc = len(data['metin'].split())
        print(f"  Words: {wc}")
        if rule and (wc < rule['min_words'] or wc > rule['max_words']):
            print(f"  ⚠️  OUT OF RANGE!")
    
    # With RAG
    print("\n🎯 WITH RAG V3:")
    result_rag = generate_question_with_rag(konu, alt_konu, rag, model, tokenizer)
    valid, msg, data = validate_question(result_rag)
    print(f"  Status: {msg}")
    if data:
        wc = len(data['metin'].split())
        print(f"  Words: {wc}")
        if rule and (rule['min_words'] <= wc <= rule['max_words']):
            print(f"  ✅ IN RANGE!")
        elif rule:
            print(f"  ⚠️  OUT OF RANGE!")

print("\n"+"="*70)
print("COMPARISON COMPLETE")
print("="*70)


## ========================================
## NEW CELL 7: Rule Compliance Test
## ========================================

def test_rule_compliance(konu, alt_konu, rag_system, model, tokenizer, n_tests=5):
    """
    Kuralara uygunluk testi
    """
    rule = rag_system.get_rule_for_question_type(konu, alt_konu)
    
    if not rule:
        print(f"⚠️  Rule not found: {konu} - {alt_konu}")
        return 0
    
    print(f"\n📋 Testing: {konu} - {alt_konu}")
    print(f"   Expected: {rule['min_words']}-{rule['max_words']} words")
    
    compliant = 0
    word_counts = []
    valid_count = 0
    
    for i in range(n_tests):
        try:
            result = generate_question_with_rag(konu, alt_konu, rag_system, model, tokenizer)
            valid, msg, data = validate_question(result)
            
            if valid and data:
                valid_count += 1
                word_count = len(data['metin'].split())
                word_counts.append(word_count)
                
                # Check compliance
                if rule['min_words'] <= word_count <= rule['max_words']:
                    compliant += 1
                    print(f"   Test {i+1}: ✅ {word_count} words (compliant)")
                else:
                    print(f"   Test {i+1}: ⚠️  {word_count} words (out of range)")
            else:
                print(f"   Test {i+1}: ❌ Invalid ({msg})")
        
        except Exception as e:
            print(f"   Test {i+1}: ❌ Error: {str(e)[:50]}")
    
    compliance_rate = (compliant / n_tests) * 100
    valid_rate = (valid_count / n_tests) * 100
    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    
    print(f"\n   📊 Results:")
    print(f"      Valid: {valid_rate:.0f}%")
    print(f"      Compliant: {compliance_rate:.0f}%")
    print(f"      Avg words: {avg_words:.0f}")
    
    return compliance_rate

# Run compliance tests
print("="*70)
print("RULE COMPLIANCE TEST (5 tests per type)")
print("="*70)

test_topics = [
    ("Paragraf", "Ana Düşünce"),
    ("Paragraf", "Başlık Bulma"),
    ("Cümlede Anlam", "Sebep-Sonuç"),
    ("Sözcükte Anlam", "Çok Anlamlılık"),
    ("Dil Bilgisi", "Fiilimsiler"),
]

total_compliance = 0
for konu, alt_konu in test_topics:
    compliance = test_rule_compliance(konu, alt_konu, rag, model, tokenizer, n_tests=5)
    total_compliance += compliance

avg_compliance = total_compliance / len(test_topics)

print("\n"+"="*70)
print(f"OVERALL COMPLIANCE: {avg_compliance:.1f}%")
print("="*70)


## ========================================
## SUMMARY
## ========================================
"""
RAG V3 INTEGRATION COMPLETE!

Cells Added:
1. Install PyYAML
2. Load RAG V3 system
3. Test RAG components
4. Enhanced prompt builder
5. RAG-enhanced generation
6. RAG vs Non-RAG comparison
7. Rule compliance test

Expected Results:
- Enhanced prompts with strategic knowledge
- Better word count compliance
- More structured questions
- Higher quality overall

Next: Run these cells and compare results!
"""
