import json, subprocess, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.agents.developer.generator import generate, DeveloperError
from backend.agents.developer.repair import run_with_repairs

req={'schema_version':'0.1.0-proposal','status':'ready_for_review','entities':[{'name':'Task','fields':[{'name':'title','type':'string'},{'name':'status','type':'enum'}],'crud':{op:{'enabled':True} for op in ['create','read','update','delete']}}]}
arch={'schema_version':'0.3.0-proposal','source':{'requirements_schema_version':'0.1.0-proposal'},'app':{'name':'Task Manager','description':'Example','language':'en','direction':'ltr'},'entity':{'name':'Task','display_field':'title','storage':{'engine':'localStorage','key':'bunyan_task'},'fields':[{'name':'title','label':'Title','type':'string','input':'text','required':True,'validation':{},'messages':{'required':'Title is required'}},{'name':'status','label':'Status','type':'enum','input':'select','required':True,'default':'to_do','options':[{'value':'to_do','label':'To do'}],'validation':{},'messages':{}}]},'screens':[{'id':'list','title':'Tasks','components':[{'type':'add_button','label':'Add Task'},{'type':'table','columns':['title','status'],'row_actions':['edit','delete']},{'type':'empty_state'}]},{'id':'form','title':'Task details','components':[{'type':'form_fields','fields':['title','status']},{'type':'save_button','label':'Save'},{'type':'cancel_button','label':'Cancel'}]}],'messages':{'empty':'No records yet','no_results':'No results','created':'Added','updated':'Updated','deleted':'Deleted'}}
with tempfile.TemporaryDirectory() as temp:
    files=generate(req,arch,temp)
    assert len(files)==3
    js=Path(files['app.js']).read_text()
    assert '__BUNYAN_CONFIG__' not in js
    subprocess.run(['node','--check',files['app.js']],check=True)
    assert 'data-testid="btn-add"' in Path(files['index.html']).read_text()
    bad={**req,'status':'needs_clarification'}
    try: generate(bad,arch,temp);raise AssertionError('Unapproved requirements accepted')
    except DeveloperError: pass
    bad_arch=json.loads(json.dumps(arch));bad_arch['entity']['fields'][0]['name']='<script>'
    try: generate(req,bad_arch,temp);raise AssertionError('Unsafe name accepted')
    except DeveloperError: pass
calls=[]
def qa(attempt):
    calls.append(('qa',attempt))
    return {'run':{'attempt':attempt},'summary':{'total':8,'passed':8 if attempt==2 else 7,'all_passed':attempt==2},'defects':[] if attempt==2 else [{'check_id':'persist_after_refresh','message':'Expected 1, received 0','evidence':{'screenshot':'failure.png'}}]}
def fix(defects,attempt): calls.append(('fix',attempt))
out=run_with_repairs(lambda:calls.append(('generate',0)),qa,fix)
assert out.attempts==2 and len(out.history)==3
assert calls==[('generate',0),('qa',0),('fix',1),('qa',1),('fix',2),('qa',2)]
print('PASS: generator output, Node syntax, rejection cases, and repair cap')
