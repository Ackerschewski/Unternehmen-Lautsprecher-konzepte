from pathlib import Path
import json
from lautsprecher_konstruktion.project.demo import demo_driver, demo_project
from lautsprecher_konstruktion.services.design import calculate_project

root=Path(__file__).resolve().parents[1]
(root/'examples').mkdir(exist_ok=True)
project=demo_project()
(root/'data'/'test_driver_demo.json').write_text(json.dumps({'drivers':[demo_driver().model_dump(mode='json')]},indent=2,ensure_ascii=False),encoding='utf-8')
(root/'examples'/'demo_2way_bassreflex.json').write_text(project.model_dump_json(indent=2),encoding='utf-8')
for kind,label in (('passive_radiator','Passivmembran'),('bandpass_4','Bandpass 4. Ordnung')):
    variant=project.model_copy(update={
        'name':f'Demo {label} - TESTDATEN',
        'enclosure':project.enclosure.model_copy(update={'enclosure_type':kind})})
    resolved=calculate_project(variant).project
    (root/'examples'/f'demo_{kind}.json').write_text(resolved.model_dump_json(indent=2),encoding='utf-8')
for key in ('woofer_frd','tweeter_frd','woofer_zma','tweeter_zma'):
    data=getattr(project.crossover,key)
    rows=['# Synthetic test data - not a physical measurement','frequency magnitude phase']
    values=data.magnitude_db if key.endswith('frd') else data.magnitude_ohm
    rows.extend(f'{f:.5f} {m:.5f} {p:.5f}' for f,m,p in zip(data.frequencies_hz,values,data.phase_deg,strict=True))
    (root/'data'/f'demo_{key}.{"frd" if key.endswith("frd") else "zma"}').write_text('\n'.join(rows)+'\n',encoding='utf-8')
