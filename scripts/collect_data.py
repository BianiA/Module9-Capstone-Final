"""Create a 10,000-row synthetic purchase snapshot from saved public API profiles."""
from pathlib import Path
import csv, json, random, hashlib, urllib.request
from datetime import date, timedelta
ROOT = Path(__file__).resolve().parents[1]

def collect(root=ROOT):
    raw = root / 'data/raw'; raw.mkdir(parents=True, exist_ok=True)
    target = raw / 'dataset.csv'
    if target.exists():
        return target  # Preserve the original input snapshot on ordinary reruns.
    sources=[]; profiles=[]
    for page in (1,2):
        url=f'https://randomuser.me/api/1.4/?results=5000&seed=capstone09-2026&page={page}&nat=ca,us,gb,au&inc=name,dob,location&format=json'
        path=raw/f'api_page_{page}.json'
        if not path.exists():
            with urllib.request.urlopen(url, timeout=90) as response: path.write_bytes(response.read())
        doc=json.loads(path.read_text())
        if len(doc.get('results',[])) != 5000: raise ValueError('Expected 5,000 profiles per API page')
        profiles.extend(doc['results'])
        sources.append({'url':url,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    rng=random.Random(20261028)
    with target.open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['CustomerID','Name','Age','PurchaseAmount','Country','Date'])
        for i,p in enumerate(profiles,1):
            cents=max(1,min(500000,round(rng.lognormvariate(9.8,0.9))))
            day=date(2025,1,1)+timedelta(days=rng.randrange(365))
            writer.writerow([i,p['name']['first']+' '+p['name']['last'],p['dob']['age'],f'{cents/100:.2f}',p['location']['country'],day.isoformat()])
    manifest={'source':'Random User Generator API v1.4 (public API alternative allowed in rubric)',
              'retrieved_date':'2026-10-28','sources':sources,'rows':len(profiles),
              'seed':20261028,'synthetic_fields':['CustomerID: sequential surrogate ID',
              'PurchaseAmount: seeded lognormal cents, mu=9.8 sigma=0.9, clamped 1..500000 cents; all amounts CAD',
              'Date: seeded uniform day in calendar 2025'],
              'note':'Names, ages and countries are synthetic API profiles. Ages are supplied API snapshot values. Purchases and dates are locally simulated, not observed transactions.',
              'dataset_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (raw/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    return target

if __name__=='__main__': print(collect())
