"""Synthetic-testable, outcome-blinded TraceAudit classifier infrastructure.

This module contains no model client and performs no network calls.
"""
from __future__ import annotations
import copy, hashlib, json, math, re, sqlite3, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from jsonschema import Draft202012Validator

SCHEMA_DIR=Path(__file__).resolve().parent/'schemas'
INPUT_SCHEMA=json.loads((SCHEMA_DIR/'classifier_input.schema.json').read_text())
OUTPUT_SCHEMA=json.loads((SCHEMA_DIR/'classifier_output.schema.json').read_text())
Draft202012Validator.check_schema(INPUT_SCHEMA); Draft202012Validator.check_schema(OUTPUT_SCHEMA)
INPUT_VALIDATOR=Draft202012Validator(INPUT_SCHEMA); OUTPUT_VALIDATOR=Draft202012Validator(OUTPUT_SCHEMA)
EVENT_FIELDS=('event_id','event_type','timestamps','indices','measurements','evidence','provenance','quality_flags')
ID_RE=re.compile(r'^[A-Za-z0-9_.-]+:EVT:[0-9]{4}$')
CITATION_RE=re.compile(r'(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_.-]+:)?EVT:[0-9]{4}(?![0-9])')
FORBIDDEN_INPUT_KEYS={'outcome','outcomes','terminaloutcome','outcomemetadata','episodeoutcome','success','successlabel','failure','failurelabel','label','labels','groundtruth','humanlabel','referencelabel','evaluation','evaluationonly','evaluationoutcome','outcomerecord'}

class ContractError(ValueError): pass

def _canonical(obj: Any) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def _errors(validator, obj):
    return [e.message for e in validator.iter_errors(obj)]

def _forbidden_keys(obj: Any, path='$'):
    found=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            norm=re.sub(r'[^a-z0-9]','',str(k).lower())
            if norm in FORBIDDEN_INPUT_KEYS or (norm.startswith('outcome') and norm!='outcomeblinded'): found.append(f'{path}.{k}')
            found.extend(_forbidden_keys(v,f'{path}.{k}'))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): found.extend(_forbidden_keys(v,f'{path}[{i}]'))
    return found

def _check_order(events, episode_id):
    ids=set(); unavailable=0
    for i,e in enumerate(events):
        eid=e['event_id']
        if eid in ids: raise ContractError(f'duplicate event_id: {eid}')
        ids.add(eid)
        match=re.fullmatch(re.escape(episode_id)+r':EVT:([0-9]{4})',eid)
        if not match or int(match.group(1))!=i+1: raise ContractError('event IDs must retain the contiguous source ordinal order')
        fr=e['indices']['frame_range']; tr=e['indices']['transition_range']
        if fr is None and tr is None: raise ContractError(f'event needs a frame or transition range: {eid}')
        for name,rng in (('frame_range',fr),('transition_range',tr)):
            if rng is not None and (len(rng)!=2 or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in rng) or rng[0]>rng[1]):
                raise ContractError(f'invalid inclusive {name}: {eid}')
        ts=e['timestamps']; vals=ts['source_values_s_unverified']
        if len(vals)!=2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in vals) or vals[0]>vals[1]:
            raise ContractError(f'invalid unverified source-time pair: {eid}')
        if e['availability']=='unavailable': unavailable+=1
    if unavailable>1: raise ContractError('at most one single-event unavailable marker is permitted')
    # The event array retains source order and its validated event-ID ordinals.
    # No event must end before the next begins: overlapping events are valid.

def validate_input(payload):
    errs=_errors(INPUT_VALIDATOR,payload)
    if errs: raise ContractError('classifier input schema: '+'; '.join(errs[:5]))
    forbidden=_forbidden_keys(payload)
    if forbidden: raise ContractError('outcome/label leakage in classifier input keys: '+', '.join(forbidden))
    episode=payload['episode_id']; events=payload['events']
    if not all(e['event_id'].startswith(episode+':EVT:') for e in events):
        raise ContractError('event ID is not linked to request episode_id')
    _check_order(events,episode)
    return True

def build_input(trace: dict, task_instruction: str):
    """Project only observed event fields; never accept outcome/evaluation records."""
    if _forbidden_keys(trace): raise ContractError('source trace contains outcome/label fields; refuse to build classifier input')
    episode_id=trace.get('episode_id')
    if not isinstance(episode_id,str) or not episode_id: raise ContractError('missing episode_id')
    if not isinstance(task_instruction,str) or not task_instruction.strip(): raise ContractError('task_instruction must be a nonempty string')
    projected=[]
    for e in trace.get('events',[]):
        missing=[k for k in EVENT_FIELDS if k not in e]
        if missing: raise ContractError(f"{e.get('event_id','event')}: missing fields {missing}")
        projected.append({**{k:copy.deepcopy(e[k]) for k in EVENT_FIELDS},'availability':'available'})
    req={'schema_version':'traceaudit-classifier-input-v0.1','episode_id':episode_id,'task_instruction':task_instruction.strip(),'outcome_blinded':True,'events':projected}
    validate_input(req)
    return req

def withhold_single_event(payload: dict, event_id: str):
    """Replace one event body with a timed unavailable marker; preserve list order."""
    validate_input(payload); out=copy.deepcopy(payload)
    matches=[i for i,e in enumerate(out['events']) if e['event_id']==event_id and e['availability']=='available']
    if len(matches)!=1: raise ContractError('withholding target must identify exactly one available event')
    i=matches[0]; e=out['events'][i]
    out['events'][i]={'event_id':e['event_id'],'availability':'unavailable','unavailable_reason':'single_event_withholding','timestamps':e['timestamps'],'indices':e['indices']}
    validate_input(out)
    if sum(e['availability']=='unavailable' for e in out['events'])!=1: raise ContractError('exactly one unavailable marker is required')
    return out

def parse_event_citations(text: str, known_event_ids):
    """Return recognized ID tokens and tokens that do not resolve to known IDs."""
    known=set(known_event_ids); found=[]; unknown=[]
    for token in CITATION_RE.findall(text or ''):
        (found if token in known else unknown).append(token)
    return {'citations':list(dict.fromkeys(found)),'unknown_citations':list(dict.fromkeys(unknown))}

def validate_output(response):
    errs=_errors(OUTPUT_VALIDATOR,response)
    if errs: raise ContractError('classifier output schema: '+'; '.join(errs[:5]))
    return True

def ground_response(payload, response):
    validate_input(payload); validate_output(response)
    by_id={e['event_id']:e for e in payload['events']}
    available={eid:e for eid,e in by_id.items() if e['availability']=='available'}
    if response['status']=='abstain': return {'grounded':True,'checked_citations':0,'reason':'abstention has no claims'}
    checked=0
    for pred in response['predictions']:
        for eid in pred['citations']:
            if eid not in available: raise ContractError(f'citation is unknown or withheld: {eid}')
            ev=available[eid]
            if not ev['evidence']: raise ContractError(f'cited event has no evidence references: {eid}')
            if any(not x.get('hdf5_path') or not x.get('hdf5_sha256') for x in ev['evidence']):
                raise ContractError(f'cited event has unresolved evidence metadata: {eid}')
            checked+=1
        inline=parse_event_citations(pred['rationale'],by_id)
        if inline['unknown_citations']: raise ContractError(f"rationale has unresolvable event citations: {inline['unknown_citations']}")
        unlisted=set(inline['citations'])-set(pred['citations'])
        if unlisted: raise ContractError(f'rationale cites events not listed in structured citations: {sorted(unlisted)}')
    return {'grounded':True,'checked_citations':checked,'reason':'all citations resolve to available input events with evidence references'}

def cache_key(request, provider, model, prompt_sha256, parameters, codebook_sha256, reference_lock_sha256):
    for name,value in (("prompt_sha256",prompt_sha256),("codebook_sha256",codebook_sha256),("reference_lock_sha256",reference_lock_sha256)):
        if not re.fullmatch(r"[a-fA-F0-9]{64}",value or ""): raise ContractError(f"{name} must be 64 hex characters")
    material={"schema":"traceaudit-response-cache-key-v0.1","request":request,"provider":provider,"model":model,"prompt_sha256":prompt_sha256,"codebook_sha256":codebook_sha256,"reference_lock_sha256":reference_lock_sha256,"parameters":parameters}
    return hashlib.sha256(_canonical(material)).hexdigest()

class ExperimentStore:
    """SQLite response cache and append-only query accounting ledger."""
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute('CREATE TABLE IF NOT EXISTS response_cache (cache_key TEXT PRIMARY KEY, response_json TEXT NOT NULL, created_at_utc TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS query_accounting (query_id TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
    def get(self,key):
        with sqlite3.connect(self.path) as c: row=c.execute('SELECT response_json FROM response_cache WHERE cache_key=?',(key,)).fetchone()
        return None if row is None else json.loads(row[0])
    def put(self,key,response):
        data=json.dumps(response,sort_keys=True,allow_nan=False); now=datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path) as c: c.execute('INSERT OR IGNORE INTO response_cache VALUES (?,?,?)',(key,data,now))
    def record(self,record):
        validate_accounting(record)
        with sqlite3.connect(self.path) as c: c.execute('INSERT INTO query_accounting VALUES (?,?)',(record['query_id'],json.dumps(record,sort_keys=True,allow_nan=False)))
    def accounting_summary(self):
        with sqlite3.connect(self.path) as c: rows=[json.loads(x[0]) for x in c.execute('SELECT record_json FROM query_accounting')]
        actual=[x for x in rows if x['provider_request_count']==1]
        return {'query_records':len(rows),'provider_requests':sum(x['provider_request_count'] for x in rows),'cache_hits':sum(x['status']=='cache_hit' for x in rows),'failed_provider_requests':sum(x['status'] in ('provider_error','invalid_response') for x in rows),'provider_request_tokens':sum(x['request_tokens'] or 0 for x in actual),'provider_response_tokens':sum(x['response_tokens'] or 0 for x in actual),'provider_total_tokens':sum((x['request_tokens'] or 0)+(x['response_tokens'] or 0) for x in actual),'token_counts_unavailable_records':sum(x['token_count_source']=='unavailable' for x in actual),'runtime_ms_total':sum(x['runtime_ms'] for x in rows)}

@dataclass
class ProviderResult:
    response: dict
    request_tokens: int|None=None
    response_tokens: int|None=None
    token_count_source: str='unavailable'

def validate_accounting(r):
    req=['query_id','cache_key','provider','model','prompt_sha256','codebook_sha256','reference_lock_sha256','status','request_tokens','response_tokens','token_count_source','runtime_ms','cache_hit','provider_request_count','created_at_utc']
    miss=[k for k in req if k not in r]
    if miss: raise ContractError(f'missing accounting fields: {miss}')
    if r['cache_hit'] not in (True,False): raise ContractError('cache_hit must be boolean')
    if r['provider_request_count']!=(0 if r['status'] in ('cache_hit','cache_invalid') else 1): raise ContractError('status/provider-request accounting mismatch')
    if r['cache_hit']!=(r['status']=='cache_hit'): raise ContractError('cache_hit/status mismatch')
    if r['status'] not in ('success','cache_hit','provider_error','invalid_response','cache_invalid'): raise ContractError('invalid query status')
    for k in ('request_tokens','response_tokens'):
        if r[k] is not None and (not isinstance(r[k],int) or isinstance(r[k],bool) or r[k]<0): raise ContractError(f'invalid {k}')
    if r['token_count_source'] not in ('provider','local_estimate','unavailable','not_applicable_cache_hit'): raise ContractError('invalid token_count_source')
    if r['status'] in ('cache_hit','cache_invalid') and r['token_count_source']!='not_applicable_cache_hit': raise ContractError('cache records cannot claim provider token usage')
    if not isinstance(r['runtime_ms'],(int,float)) or isinstance(r['runtime_ms'],bool) or r['runtime_ms']<0: raise ContractError('runtime_ms must be nonnegative')
    for k in ('cache_key','prompt_sha256','codebook_sha256','reference_lock_sha256'):
        if not re.fullmatch(r'[a-fA-F0-9]{64}',r[k]): raise ContractError(f'invalid {k}')
    try: datetime.fromisoformat(r['created_at_utc'].replace('Z','+00:00'))
    except Exception as e: raise ContractError('created_at_utc must be ISO-8601') from e

def assert_experiment_ready(*,codebook_frozen_sha256=None,prompt_frozen_sha256=None,reference_lock_sha256=None,codebook_frozen=False,prompt_frozen=False,reference_lock_verified=False,explicit_authorization=False):
    """Fail closed until all preconditions for a real experiment exist."""
    if not all(isinstance(x,str) and re.fullmatch(r'[a-fA-F0-9]{64}',x) for x in (codebook_frozen_sha256,prompt_frozen_sha256,reference_lock_sha256)):
        raise ContractError('codebook, prompt, and reference-lock freeze hashes are required')
    if codebook_frozen is not True or prompt_frozen is not True: raise ContractError('codebook and prompt must both be explicitly frozen')
    if reference_lock_verified is not True: raise ContractError('reference sample lock must be verified')
    if explicit_authorization is not True: raise ContractError('explicit authorization for real LLM evaluation is required')
    return True

def execute_cached(store: ExperimentStore, request, *, provider: str, model: str, prompt_sha256: str, codebook_sha256: str, reference_lock_sha256: str, parameters: dict, query_id: str, codebook_frozen: bool, prompt_frozen: bool, reference_lock_verified: bool, explicit_authorization: bool, call: Callable[[],ProviderResult]):
    """Use a caller-supplied provider only after freeze/authorization gates.

    No provider is bundled. Tests pass only a synthetic local callback.
    """
    validate_input(request)
    assert_experiment_ready(codebook_frozen_sha256=codebook_sha256,prompt_frozen_sha256=prompt_sha256,reference_lock_sha256=reference_lock_sha256,codebook_frozen=codebook_frozen,prompt_frozen=prompt_frozen,reference_lock_verified=reference_lock_verified,explicit_authorization=explicit_authorization)
    key=cache_key(request,provider,model,prompt_sha256,parameters,codebook_sha256,reference_lock_sha256)
    start=time.perf_counter(); cached=store.get(key)
    base={'query_id':query_id,'cache_key':key,'provider':provider,'model':model,'prompt_sha256':prompt_sha256,'codebook_sha256':codebook_sha256,'reference_lock_sha256':reference_lock_sha256,'created_at_utc':datetime.now(timezone.utc).isoformat()}
    if cached is not None:
        try:
            validate_output(cached); ground_response(request,cached)
        except Exception:
            record={**base,'status':'cache_invalid','request_tokens':None,'response_tokens':None,'token_count_source':'not_applicable_cache_hit','runtime_ms':(time.perf_counter()-start)*1000,'cache_hit':False,'provider_request_count':0}
            store.record(record); raise ContractError('cached response failed current schema/grounding checks')
        record={**base,'status':'cache_hit','request_tokens':None,'response_tokens':None,'token_count_source':'not_applicable_cache_hit','runtime_ms':(time.perf_counter()-start)*1000,'cache_hit':True,'provider_request_count':0}
        store.record(record); return cached,record
    started=time.perf_counter()
    try: result=call()
    except Exception:
        record={**base,'status':'provider_error','request_tokens':None,'response_tokens':None,'token_count_source':'unavailable','runtime_ms':(time.perf_counter()-started)*1000,'cache_hit':False,'provider_request_count':1}
        store.record(record); raise
    elapsed=(time.perf_counter()-started)*1000
    if not isinstance(result,ProviderResult): result=ProviderResult(response=result)
    try:
        validate_output(result.response); ground_response(request,result.response)
    except Exception:
        record={**base,'status':'invalid_response','request_tokens':result.request_tokens,'response_tokens':result.response_tokens,'token_count_source':result.token_count_source,'runtime_ms':elapsed,'cache_hit':False,'provider_request_count':1}
        store.record(record); raise
    record={**base,'status':'success','request_tokens':result.request_tokens,'response_tokens':result.response_tokens,'token_count_source':result.token_count_source,'runtime_ms':elapsed,'cache_hit':False,'provider_request_count':1}
    store.put(key,result.response); store.record(record); return result.response,record
