"""Validate, enrich, load SQLite, and publish an analytical snapshot with real run logs."""
from pathlib import Path
import argparse,csv,json,sqlite3,logging,hashlib,time,sys,os,uuid
from datetime import datetime,timezone,date
from decimal import Decimal,InvalidOperation
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['CustomerID','Name','Age','PurchaseAmount','Country','Date']

def age_group(age):
    return 'Teen' if age<=18 else 'Young Adult' if age<=35 else 'Adult' if age<=50 else 'Senior'
def purchase_category(cents):
    return 'Low' if cents<=10000 else 'Medium' if cents<=50000 else 'High' if cents<=100000 else 'VIP'

def clean_rows(rows,lookup):
    cleaned=[];rejects=[];seen=set();duplicates=0
    for number,row in enumerate(rows,2):
        try:
            if any(row.get(k) is None or not str(row[k]).strip() for k in FIELDS): raise ValueError('missing required value')
            cid=int(str(row['CustomerID']).strip());age=int(str(row['Age']).strip())
            if cid<=0 or not 0<=age<=120: raise ValueError('ID or age out of range')
            name=' '.join(row['Name'].split());country=row['Country'].strip()
            amount=Decimal(str(row['PurchaseAmount']).strip())
            if not amount.is_finite() or amount<=0 or amount>5000 or amount!=amount.quantize(Decimal('.01')): raise ValueError('invalid amount')
            cents=int(amount*100);day=date.fromisoformat(row['Date'].strip())
            if day.year!=2025: raise ValueError('date outside reporting year 2025')
            if country not in lookup: raise ValueError('unknown country')
            record=(cid,name,age,cents,country,day.isoformat())
            if record in seen: duplicates+=1;continue
            seen.add(record)
            cleaned.append(dict(customer_id=cid,name=name,age=age,purchase_amount=float(amount),country=country,date=day.isoformat(),
                          age_group=age_group(age),purchase_category=purchase_category(cents),country_code=lookup[country]['country_code'],
                          region=lookup[country]['region'],year_month=day.strftime('%Y-%m'),purchase_cents=cents,currency='CAD'))
        except (ValueError,TypeError,InvalidOperation) as e:
            rejects.append({'source_row':number,'reason':str(e),'record':row})
    # A customer appears once in this source grain. Conflicting duplicate IDs fail the run.
    ids=[r['customer_id'] for r in cleaned]
    if len(ids)!=len(set(ids)): raise ValueError('Conflicting duplicate CustomerID')
    return sorted(cleaned,key=lambda r:r['customer_id']),rejects,duplicates

def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    os.replace(temp,path)

def run(root=ROOT,raw_path=None,expected_rows=10000):
    root=Path(root); logdir=root/'logs';logdir.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('capstone.'+uuid.uuid4().hex);logger.setLevel(logging.INFO)
    handler=logging.FileHandler(logdir/'pipeline.log',encoding='utf-8');handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(handler)
    start=time.perf_counter();run_id=uuid.uuid4().hex;status={'run_id':run_id,'started_utc':datetime.now(timezone.utc).isoformat(),'status':'running'}
    dbtemp=root/'data/capstone.tmp.sqlite'
    try:
        logger.info('START run_id=%s',run_id)
        raw=Path(raw_path) if raw_path else root/'data/raw/dataset.csv'
        raw_hash=hashlib.sha256(raw.read_bytes()).hexdigest()
        with raw.open(newline='',encoding='utf-8') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=FIELDS: raise ValueError('Raw schema does not match required six columns')
            rows=list(reader)
        if len(rows)!=expected_rows: raise ValueError(f'Expected {expected_rows} raw rows, got {len(rows)}')
        logger.info('INGEST raw_rows=%s sha256=%s',len(rows),raw_hash)
        with (root/'data/reference/country_lookup.csv').open(newline='') as f: refs=list(csv.DictReader(f))
        if len({r['country'] for r in refs})!=len(refs): raise ValueError('Duplicate reference country')
        lookup={r['country']:r for r in refs}
        clean,rejects,dupes=clean_rows(rows,lookup)
        (logdir/'rejected_rows.json').write_text(json.dumps(rejects,indent=2))
        logger.info('CLEAN accepted=%s rejected=%s exact_duplicates=%s',len(clean),len(rejects),dupes)
        # Fail closed: no partial analytics snapshot is published when input checks fail.
        if rejects or dupes or len(clean)!=expected_rows: raise ValueError('Quality gate failed; inspect rejected_rows.json and pipeline.log')
        if any(any(v is None or v=='' for v in r.values()) for r in clean): raise ValueError('Enrichment introduced missing values')
        logger.info('ENRICH many-to-one country join validated; derived age/category/month/currency')
        dbtemp.unlink(missing_ok=True)
        with closing(sqlite3.connect(dbtemp)) as con:
            con.executescript((root/'sql/schema.sql').read_text());con.execute('PRAGMA foreign_keys=ON')
            con.executemany('INSERT INTO dim_country VALUES(?,?,?)',[(r['country_code'],r['country'],r['region']) for r in refs])
            con.executemany('INSERT INTO dim_customer VALUES(?,?,?,?)',[(r['customer_id'],r['name'],r['age'],r['age_group']) for r in clean])
            dates=sorted({r['date'] for r in clean})
            con.executemany('INSERT INTO dim_date VALUES(?,?,?,?)',[(d,int(d[:4]),int(d[5:7]),d[:7]) for d in dates])
            con.executemany('INSERT INTO fact_purchase VALUES(?,?,?,?,?,?,?)',[(i,r['customer_id'],r['country_code'],r['date'],r['purchase_cents'],r['purchase_category'],'CAD') for i,r in enumerate(clean,1)])
            if con.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Foreign key validation failed')
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('SQLite integrity failed')
            n,total=con.execute('SELECT COUNT(*),SUM(purchase_cents) FROM fact_purchase').fetchone()
            if n!=len(clean) or total!=sum(r['purchase_cents'] for r in clean): raise ValueError('Source-target reconciliation failed')
            cursor=con.execute('SELECT * FROM analytics_purchases ORDER BY purchase_id');names=[d[0] for d in cursor.description];loaded=[dict(zip(names,x)) for x in cursor]
            summary={'rows':n,'customers':len(clean),'revenue_cents':total,'revenue_cad':total/100,'average_purchase_cad':total/100/n,'countries':len(refs),'min_date':dates[0],'max_date':dates[-1],
                     'country':[dict(zip(['country','purchases','revenue_cents'],r)) for r in con.execute('SELECT country,COUNT(*),SUM(purchase_cents) FROM analytics_purchases GROUP BY country ORDER BY SUM(purchase_cents) DESC')],
                     'monthly':[dict(zip(['month','revenue_cents'],r)) for r in con.execute('SELECT year_month,SUM(purchase_cents) FROM analytics_purchases GROUP BY year_month ORDER BY year_month')],
                     'age':[dict(zip(['age_group','purchases','revenue_cents'],r)) for r in con.execute('SELECT age_group,COUNT(*),SUM(purchase_cents) FROM analytics_purchases GROUP BY age_group')],
                     'category':[dict(zip(['category','purchases'],r)) for r in con.execute('SELECT purchase_category,COUNT(*) FROM analytics_purchases GROUP BY purchase_category')]}
            con.commit()
        os.replace(dbtemp,root/'data/capstone.sqlite')
        write_csv(root/'data/cleaned/dataset_final.csv',loaded,names)
        write_csv(root/'data/cleaned/dataset_enriched.csv',clean,list(clean[0]))
        if hashlib.sha256(raw.read_bytes()).hexdigest()!=raw_hash: raise ValueError('Raw snapshot was modified')
        (root/'data/cleaned/summary.json').write_text(json.dumps(summary,indent=2))
        checks={'raw_rows':len(rows),'accepted_rows':len(clean),'rejected_rows':len(rejects),'duplicates_removed':dupes,'null_values':0,'foreign_key_violations':0,'source_target_rows_match':True,'source_target_cents_match':True,'raw_sha256':raw_hash,'raw_unchanged':True}
        (logdir/'validation.json').write_text(json.dumps(checks,indent=2))
        logger.info('LOAD target_rows=%s revenue_cents=%s integrity=ok',n,total)
        status.update(status='success',rows=n,revenue_cents=total)
        return summary
    except Exception as e:
        status.update(status='failed',error=str(e));logger.exception('FAILED run_id=%s',run_id);raise
    finally:
        dbtemp.unlink(missing_ok=True)
        status['duration_seconds']=round(time.perf_counter()-start,4);status['finished_utc']=datetime.now(timezone.utc).isoformat()
        (logdir/'last_run.json').write_text(json.dumps(status,indent=2))
        with (logdir/'run_history.jsonl').open('a') as f:f.write(json.dumps(status)+'\n')
        logger.info('END status=%s duration_seconds=%s',status['status'],status['duration_seconds']);handler.close();logger.removeHandler(handler)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--input',type=Path);args=parser.parse_args()
    try: print(json.dumps(run(args.root,args.input),indent=2))
    except Exception: sys.exit(1)
