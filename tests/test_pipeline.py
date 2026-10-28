from pathlib import Path
import sys,tempfile,shutil,csv,json,unittest,sqlite3,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import clean_rows,run,age_group,purchase_category,ROOT

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.lookup={'Canada':{'country_code':'CA','region':'North America'}}
  self.row=dict(CustomerID='1',Name='  Jane   Sample ',Age='35',PurchaseAmount='100.00',Country='Canada',Date='2025-01-01')
 def test_boundaries(self):
  self.assertEqual([age_group(x) for x in [18,19,35,36,50,51]],['Teen','Young Adult','Young Adult','Adult','Adult','Senior'])
  self.assertEqual([purchase_category(x) for x in [1,10000,10001,50000,50001,100000,100001,500000]],['Low','Low','Medium','Medium','High','High','VIP','VIP'])
 def test_clean_and_duplicate(self):
  good,bad,duplicates=clean_rows([self.row,self.row],self.lookup)
  self.assertEqual((len(good),len(bad),duplicates),(1,0,1));self.assertEqual(good[0]['name'],'Jane Sample');self.assertEqual(good[0]['purchase_cents'],10000)
 def test_bad_records_quarantined(self):
  for key,value in [('Name',''),('Age','121'),('Age','35.5'),('PurchaseAmount','NaN'),('PurchaseAmount','0'),('PurchaseAmount','5.123'),('Date','2025-02-30'),('Country','Unknown')]:
   with self.subTest(key=key,value=value):
    good,bad,_=clean_rows([{**self.row,key:value}],self.lookup);self.assertEqual(len(good),0);self.assertEqual(len(bad),1)
 def test_conflicting_ids_fail(self):
  with self.assertRaises(ValueError):clean_rows([self.row,{**self.row,'Name':'Other'}],self.lookup)
 def test_reconciliation_idempotence_and_failure(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   shutil.copytree(ROOT/'data/raw',root/'data/raw');shutil.copytree(ROOT/'data/reference',root/'data/reference');shutil.copytree(ROOT/'sql',root/'sql')
   first=run(root);before=(root/'data/cleaned/dataset_final.csv').read_bytes();raw=(root/'data/raw/dataset.csv').read_bytes()
   second=run(root)
   self.assertEqual(first,second);self.assertEqual(before,(root/'data/cleaned/dataset_final.csv').read_bytes());self.assertEqual(raw,(root/'data/raw/dataset.csv').read_bytes())
   database=(root/'data/capstone.sqlite').read_bytes()
   with (root/'data/raw/dataset.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
   rows[0]['Country']='Unknown'
   badfile=root/'bad.csv'
   with badfile.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
   with self.assertRaises(ValueError):run(root,badfile)
   self.assertEqual(json.loads((root/'logs/last_run.json').read_text())['status'],'failed')
   self.assertEqual(database,(root/'data/capstone.sqlite').read_bytes());self.assertEqual(before,(root/'data/cleaned/dataset_final.csv').read_bytes())
   self.assertIn('FAILED',(root/'logs/pipeline.log').read_text())

if __name__=='__main__':unittest.main()
