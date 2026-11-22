"""Recreate the national CSV from the exact frozen original Ember download."""
from pathlib import Path
import csv, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'data/provenance.json').read_text())
source=next(s for s in manifest['sources'] if s['path']=='data/raw/ember_monthly_global.csv')
raw=ROOT/source['path']
assert hashlib.sha256(raw.read_bytes()).hexdigest()==source['sha256'], 'Frozen raw file changed'
with raw.open(newline='') as f:
    rows=[{'Date':r['Date'],'Generation_TWh':r['Generation (TWh)']}
          for r in csv.DictReader(f)
          if r['Area']=='Kazakhstan' and r['Electricity source']=='Total generation']
rows.sort(key=lambda r:r['Date'])
assert len(rows)==102
target=ROOT/'data/kazakhstan_generation_snapshot.csv'
with target.open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['Date','Generation_TWh'])
    writer.writeheader(); writer.writerows(rows)
expected=next(s['sha256'] for s in manifest['sources'] if s['path']==str(target.relative_to(ROOT)))
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
print('Extracted 102 unchanged monthly observations; SHA-256 matches the published snapshot.')
