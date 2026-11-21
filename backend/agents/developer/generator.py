"""Deterministic Developer Agent: fill Naifah's fixed architecture into CRUD files.

No LLM or API key is needed. The caller must enforce user approval before this step.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / 'templates' / 'crud'
SUPPORTED_INPUTS = {'text', 'textarea', 'number', 'checkbox', 'date', 'time', 'datetime-local', 'email', 'tel', 'url', 'select'}

class DeveloperError(ValueError):
    pass

def validate(requirements: dict, architecture: dict) -> None:
    if requirements.get('status') != 'ready_for_review':
        raise DeveloperError('Requirements must be ready_for_review and separately approved by the user')
    entities = requirements.get('entities') or []
    if len(entities) != 1:
        raise DeveloperError('MVP supports exactly one entity')
    if len(architecture.get('entity', {}).get('fields', [])) > 12:
        raise DeveloperError('MVP supports at most 12 fields')
    if architecture.get('entity', {}).get('name') != entities[0].get('name'):
        raise DeveloperError('Architecture entity does not match requirements')
    if architecture.get('source', {}).get('requirements_schema_version') != requirements.get('schema_version'):
        raise DeveloperError('Architecture source schema version does not match requirements')
    if architecture.get('entity', {}).get('storage', {}).get('engine') != 'localStorage':
        raise DeveloperError('Only localStorage is supported')
    if len(architecture.get('screens') or []) != 2 or {s.get('id') for s in architecture['screens']} != {'list','form'}:
        raise DeveloperError('Expected list and form screens')
    if any(not entities[0].get('crud', {}).get(op, {}).get('enabled') for op in ('create','read','update','delete')):
        raise DeveloperError('All CRUD operations must be enabled')
    req_fields = {f['name']:f for f in entities[0].get('fields', [])}
    arch_fields = architecture['entity']['fields']
    if len(req_fields) != len(arch_fields):
        raise DeveloperError('Requirements/architecture fields mismatch')
    for field in arch_fields:
        name=field.get('name','')
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*', name):
            raise DeveloperError(f'Unsafe field name: {name!r}')
        if name not in req_fields or field.get('type') != req_fields[name].get('type'):
            raise DeveloperError(f'Field mismatch: {name}')
        if field.get('input') not in SUPPORTED_INPUTS:
            raise DeveloperError(f'Unsupported input: {field.get("input")}')
        if field.get('type') == 'reference':
            raise DeveloperError('Reference fields are not supported')
    if architecture['entity'].get('display_field') not in req_fields:
        raise DeveloperError('Unknown display field')
    if not re.fullmatch(r'bunyan_[a-z0-9_]+', architecture['entity']['storage'].get('key','')):
        raise DeveloperError('Invalid localStorage key')
    list_screen = next(s for s in architecture['screens'] if s['id']=='list')
    if not any(c.get('type')=='table' for c in list_screen.get('components',[])):
        raise DeveloperError('List screen requires a table component')

def generate(requirements: dict, architecture: dict, output_dir: str | Path) -> dict[str,str]:
    validate(requirements, architecture)
    out = Path(output_dir).resolve()
    out.mkdir(parents=True,exist_ok=True)
    config=json.dumps(architecture,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    files={}
    for filename in ('index.html','style.css','app.js'):
        source=(TEMPLATE_DIR / filename).read_text(encoding='utf-8')
        if filename=='app.js': source=source.replace('__BUNYAN_CONFIG__',config)
        (out/filename).write_text(source,encoding='utf-8')
        files[filename]=str(out/filename)
    return files

def main():
    p=argparse.ArgumentParser(description='Generate a BUNYAN CRUD app from approved contracts')
    p.add_argument('--requirements',required=True)
    p.add_argument('--architecture',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    req=json.loads(Path(args.requirements).read_text(encoding='utf-8'))
    arch=json.loads(Path(args.architecture).read_text(encoding='utf-8'))
    print(json.dumps(generate(req,arch,args.out),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
