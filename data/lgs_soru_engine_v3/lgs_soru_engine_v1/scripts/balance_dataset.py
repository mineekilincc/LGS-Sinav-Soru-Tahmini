# Reproduce balancing (v1)
from pathlib import Path
import json, random
from collections import defaultdict

SRC = Path('data/processed/normalized_merged_v2.jsonl')
OUT = Path('data/processed')
SEED=42
MIN_COUNT=15
TARGET_COUNT=20
random.seed(SEED)

rows=[json.loads(l) for l in SRC.open(encoding='utf-8')]
by=defaultdict(list)
for r in rows:
    by[r['canonical_subtopic']].append(r)

eligible={k:v for k,v in by.items() if len(v)>=MIN_COUNT}
sel=[]
for k,items in eligible.items():
    if len(items)>TARGET_COUNT:
        sel.extend(random.sample(items,TARGET_COUNT))
    else:
        sel.extend(items)

random.shuffle(sel)

def split(items, val_frac=0.1, test_frac=0.1):
    by=defaultdict(list)
    for it in items:
        by[it['canonical_subtopic']].append(it)
    train=[]; val=[]; test=[]
    for k,grp in by.items():
        random.shuffle(grp)
        n=len(grp)
        n_test=max(1,int(round(n*test_frac)))
        n_val=max(1,int(round(n*val_frac)))
        if n_test+n_val>=n:
            n_test=max(0,n_test-1)
        test.extend(grp[:n_test])
        val.extend(grp[n_test:n_test+n_val])
        train.extend(grp[n_test+n_val:])
    random.shuffle(train); random.shuffle(val); random.shuffle(test)
    return train,val,test

train,val,test=split(sel)
for name,data in [('train_balanced_v1.jsonl',train),('val_balanced_v1.jsonl',val),('test_balanced_v1.jsonl',test)]:
    with (OUT/name).open('w',encoding='utf-8') as f:
        for r in data:
            f.write(json.dumps(r, ensure_ascii=False)+'\n')
print('Wrote',len(train),len(val),len(test))
