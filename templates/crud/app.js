/* BUNYAN generated application: configuration is injected by generator.py. */
const CONFIG = __BUNYAN_CONFIG__;
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const E = CONFIG.entity;
  const fields = E.fields;
  const fieldMap = Object.fromEntries(fields.map(f => [f.name, f]));
  const listScreen = CONFIG.screens.find(s => s.id === 'list');
  const formScreen = CONFIG.screens.find(s => s.id === 'form');
  const components = listScreen.components;
  const table = components.find(c => c.type === 'table');
  const search = components.find(c => c.type === 'search');
  const filters = components.find(c => c.type === 'filters');
  const storageKey = E.storage.key;
  const messages = CONFIG.messages;
  const isArabic = CONFIG.app.language === 'ar';
  let editingId = null, query = '', activeFilters = {};
  const element = (tag, attrs = {}, value) => { const n = document.createElement(tag); Object.entries(attrs).forEach(([k,v]) => n.setAttribute(k,v)); if(value !== undefined) n.textContent = String(value); return n; };
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
  const load = () => { try { const x = JSON.parse(localStorage.getItem(storageKey) || '[]'); return Array.isArray(x) ? x : []; } catch { return []; } };
  const store = rows => { try { localStorage.setItem(storageKey, JSON.stringify(rows)); return true; } catch { toast(isArabic?'تعذر حفظ البيانات':'Could not save records'); return false; } };
  const toast = message => { $('toast').textContent=message; $('toast').hidden=false; };
  const display = (field, value) => { if(value == null || value === '') return ''; if(field?.type === 'enum') return field.options?.find(o=>o.value===value)?.label ?? String(value); if(field?.type === 'boolean') return value ? (isArabic?'نعم':'Yes') : (isArabic?'لا':'No'); if(field?.display_format?.decimals != null && value !== '') return Number(value).toFixed(field.display_format.decimals); return String(value); };
  const cols = table.columns;
  const listRecords = () => {
    let records = load();
    if(query && search) records = records.filter(r => search.fields.some(n => String(r[n] ?? '').toLowerCase().includes(query)));
    for(const [key,val] of Object.entries(activeFilters)) if(val !== '') records = records.filter(r => String(r[key] ?? '') === val);
    if(table.sort?.field){ const {field,direction} = table.sort; records.sort((a,b)=>String(a[field]??'').localeCompare(String(b[field]??''),undefined,{numeric:true})*(direction==='desc'?-1:1)); }
    return records;
  };
  function renderList(){
    const records = listRecords(); const tbody = $('rows'); tbody.replaceChildren();
    for(const record of records){
      const tr=element('tr',{'data-testid':'record-row','data-id':record.id});
      for(const name of cols) tr.append(element('td',{'data-testid':`cell-${name}`},display(fieldMap[name],record[name])));
      const actions=element('td');
      const edit=element('button',{type:'button','data-testid':'btn-edit'},messages.edit_button||'Edit'); edit.addEventListener('click',()=>openForm(record));
      const del=element('button',{type:'button','data-testid':'btn-delete'},messages.delete_button||'Delete');
      del.addEventListener('click',()=>{
        if(actions.querySelector('.confirm')) return;
        const confirm=element('div',{class:'confirm'});
        confirm.append(element('span',{'data-testid':'confirm-delete-text'},(messages.confirm_delete||'Delete {display}?').replace('{display}',String(record[E.display_field]??''))));
        const yes=element('button',{type:'button','data-testid':'btn-confirm-delete'},messages.confirm_button||'Confirm');
        const no=element('button',{type:'button','data-testid':'btn-cancel-delete'},messages.cancel_delete_button||'Cancel');
        yes.addEventListener('click',()=>{if(store(load().filter(r=>r.id!==record.id))){toast(messages.deleted||'Deleted');renderList();}});
        no.addEventListener('click',()=>confirm.remove()); confirm.append(yes,no);actions.append(confirm);
      }); actions.append(edit,del);tr.append(actions);tbody.append(tr);
    }
    $('empty').hidden=load().length!==0;
    $('no-results').hidden=load().length===0 || records.length!==0;
  }
  function buildControl(f,record){
    let input;
    if(f.input==='select'){
      input=element('select');
      if(f.empty_option) input.append(element('option',{value:''},f.empty_option));
      for(const o of f.options||[]) input.append(element('option',{value:o.value},o.label));
    } else if(f.input==='textarea') input=element('textarea');
    else input=element('input',{type:f.input==='checkbox'?'checkbox':f.input});
    input.name=f.name;input.setAttribute('data-testid',`input-${f.name}`);
    if(f.step!=null) input.step=String(f.step);
    const value=record ? record[f.name] : f.default;
    if(f.input==='checkbox') input.checked=Boolean(value);
    else input.value=value == null ? '' : String(value);
    return input;
  }
  function openForm(record){
    editingId=record?.id??null; const form=$('record-form');form.replaceChildren();
    for(const f of fields){
      const wrap=element('label',{class:'field'},`${f.label}${f.required?' *':''}`);
      const input=buildControl(f,record);const error=element('span',{'data-testid':`error-${f.name}`,class:'error'});error.hidden=true;
      wrap.append(input,error);form.append(wrap);
    }
    $('form-title').textContent=formScreen.title;
    $('screen-list').hidden=true;$('screen-form').hidden=false;
  }
  function closeForm(){editingId=null;$('screen-form').hidden=true;$('screen-list').hidden=false;renderList();}
  function collect(){const values={};for(const f of fields){const input=$('record-form').elements.namedItem(f.name);if(f.type==='boolean')values[f.name]=input.checked;else if((f.type==='integer'||f.type==='decimal')&&input.value.trim()!=='') values[f.name]=Number(input.value);else values[f.name]=input.value.trim();}return values;}
  function validate(values){
    const errors={};const existing=load();
    for(const f of fields){
      const value=values[f.name],v=f.validation||{},m=f.messages||{};
      const empty=value===''||value===null||value===undefined;
      if(f.required&&empty){errors[f.name]=m.required||`${f.label} is required`;continue;}
      if(empty)continue;
      const str=String(value);
      if(v.min_length!=null&&str.length<v.min_length)errors[f.name]=m.min_length||'Too short';
      else if(v.max_length!=null&&str.length>v.max_length)errors[f.name]=m.max_length||'Too long';
      else if(v.pattern){try{if(!new RegExp(v.pattern).test(str))errors[f.name]=m.pattern||'Invalid format';}catch{errors[f.name]=m.pattern||'Invalid format';}}
      if(!errors[f.name]&&(f.type==='integer'||f.type==='decimal')){
        if(!Number.isFinite(value)||(f.type==='integer'&&!Number.isInteger(value)))errors[f.name]=m.invalid||'Invalid number';
        else if(v.min_value!=null&&value<v.min_value)errors[f.name]=m.min_value||'Below minimum';
        else if(v.max_value!=null&&value>v.max_value)errors[f.name]=m.max_value||'Above maximum';
      }
      if(!errors[f.name]&&v.date_constraint){const date=str.slice(0,10);if(v.date_constraint==='not_in_past'&&date<today())errors[f.name]=m.date_constraint||'Date cannot be in the past';if(v.date_constraint==='not_in_future'&&date>today())errors[f.name]=m.date_constraint||'Date cannot be in the future';}
      if(!errors[f.name]&&f.type==='enum'&&!(f.options||[]).some(o=>o.value===value))errors[f.name]=m.invalid||'Invalid selection';
      if(!errors[f.name]&&f.unique&&existing.some(r=>r.id!==editingId&&String(r[f.name])===str))errors[f.name]=m.unique||'Already exists';
    }
    return errors;
  }
  function save(){
    const values=collect(),errors=validate(values);
    for(const f of fields){const e=$('record-form').querySelector(`[data-testid="error-${f.name}"]`);e.textContent=errors[f.name]||'';e.hidden=!errors[f.name];}
    if(Object.keys(errors).length)return;
    const records=load(),now=new Date().toISOString();
    if(editingId){const i=records.findIndex(r=>r.id===editingId);if(i<0){toast('Record not found');return;}records[i]={...records[i],...values,updated_at:now};}
    else records.push({id:crypto.randomUUID(),...values,created_at:now,updated_at:now});
    if(store(records)){toast(editingId?(messages.updated||'Updated'):(messages.created||'Created'));closeForm();}
  }
  function init(){
    document.documentElement.lang=CONFIG.app.language;document.documentElement.dir=CONFIG.app.direction;
    document.title=CONFIG.app.name;$('app-title').textContent=CONFIG.app.name;$('app-description').textContent=CONFIG.app.description;
    $('list-title').textContent=listScreen.title;$('add').textContent=components.find(c=>c.type==='add_button')?.label||'Add';
    $('save').textContent=formScreen.components.find(c=>c.type==='save_button')?.label||'Save';$('cancel').textContent=formScreen.components.find(c=>c.type==='cancel_button')?.label||'Cancel';
    $('empty').textContent=messages.empty;$('no-results').textContent=messages.no_results||'No results';
    const header=element('tr');for(const name of cols)header.append(element('th',{},fieldMap[name]?.label||name));header.append(element('th',{},isArabic?'إجراءات':'Actions'));$('head').append(header);
    if(search){const input=element('input',{'data-testid':'search-input',placeholder:search.placeholder||'Search'});input.addEventListener('input',()=>{query=input.value.toLowerCase().trim();renderList();});$('controls').append(input);}
    if(filters)for(const name of filters.fields){const f=fieldMap[name],select=element('select',{'data-testid':`filter-${name}`});select.append(element('option',{value:''},f.label));for(const o of f.options||[])select.append(element('option',{value:o.value},o.label));select.addEventListener('change',()=>{activeFilters[name]=select.value;renderList();});$('controls').append(select);}
    $('add').addEventListener('click',()=>openForm(null));$('save').addEventListener('click',save);$('cancel').addEventListener('click',closeForm);renderList();
  }
  init();
})();
