"""Regenerate static dashboard from the validated SQLite-derived summary."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'data/cleaned/summary.json').read_text())
fig,axs=plt.subplots(2,2,figsize=(13,8));fig.patch.set_facecolor('#f4f6fa')
fig.suptitle('Synthetic customer purchases | 2025',x=.06,ha='left',fontsize=22,weight='bold',color='#23395b')
fig.text(.06,.9,f"{s['rows']:,} purchases     CAD {s['revenue_cad']:,.2f} total     CAD {s['average_purchase_cad']:,.2f} average",fontsize=13)
a=axs[0,0];data=list(reversed(s['country']));a.barh([r['country'] for r in data],[r['revenue_cents']/100 for r in data],color='#4169a1');a.set_title('Purchase value by country (CAD)');a.set_xlim(left=0)
a=axs[0,1];a.plot([r['month'][5:] for r in s['monthly']],[r['revenue_cents']/100 for r in s['monthly']],color='#875bb4',marker='o');a.set_title('Monthly purchase value (CAD)');a.set_xlabel('Month of 2025')
a=axs[1,0];order=['Low','Medium','High','VIP'];mapping={r['category']:r['purchases'] for r in s['category']};a.bar(order,[mapping.get(k,0) for k in order],color='#2f8a7c');a.set_title('Purchases by spending category');a.set_ylabel('Purchases')
a=axs[1,1];order=['Teen','Young Adult','Adult','Senior'];mapping={r['age_group']:r['purchases'] for r in s['age']};a.bar(order,[mapping.get(k,0) for k in order],color='#c18a3b');a.set_title('Purchases by age group');a.set_ylabel('Purchases')
for a in axs.flat:a.spines[['top','right']].set_visible(False);a.tick_params(labelsize=9)
fig.text(.06,.025,'Synthetic API profiles with simulated CAD amounts and dates. Differences describe this sample, not real customer behavior.',fontsize=9,color='#526277')
fig.tight_layout(rect=(.03,.06,.98,.86));out=ROOT/'dashboards';out.mkdir(exist_ok=True);fig.savefig(out/'dashboard_preview.png',dpi=160);plt.close(fig)
print(out/'dashboard_preview.png')
