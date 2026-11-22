"""Extract the audited national total directly from each original Samruk DOCX."""
from pathlib import Path
import zipfile,xml.etree.ElementTree as ET,json,csv,hashlib
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
manifest=json.loads((ROOT/'data/provenance.json').read_text())
result={}
for name,period in [('samruk_2018_january.docx','2018-01'),('samruk_2018_q1.docx','2018-Q1')]:
    path=ROOT/'data/source_checks'/name
    expected=next(s['sha256'] for s in manifest['sources'] if s['path']==str(path.relative_to(ROOT)))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    with zipfile.ZipFile(path) as z: doc=ET.fromstring(z.read('word/document.xml'))
    table=doc.findall('.//w:tbl',NS)[0]
    rows=[[''.join(t.text or '' for t in cell.findall('.//w:t',NS)).strip()
           for cell in row.findall('w:tc',NS)] for row in table.findall('w:tr',NS)]
    national=next(row for row in rows if row[:2]==['Казахстан','Всего'])
    # Original table: Kazakhstan / Total / 2017 / 2018 / percentage change.
    decimal_value=Decimal(national[3].replace('\xa0','').replace(' ','').replace(',','.'))
    million_kwh=float(decimal_value)
    result[period]={'original_table_row':national,'unit':'million kWh',
                    'value_2018':million_kwh,'TWh':float(decimal_value/Decimal(1000))}
assert result['2018-01']['TWh']==10.3573
assert result['2018-Q1']['TWh']==29.3392
with (ROOT/'data/kazakhstan_generation_snapshot.csv').open() as f: series=list(csv.DictReader(f))
result['ember']={'2018-01':float(series[0]['Generation_TWh']),
                 '2018-Q1_sum':sum(float(r['Generation_TWh']) for r in series[:3])}
result['interpretation']='The quarterly total nearly matches, while the individual January value differs. Averaging is plausible but not proven as the construction rule for all values.'
(ROOT/'results/source_checks.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,indent=2,ensure_ascii=False))
