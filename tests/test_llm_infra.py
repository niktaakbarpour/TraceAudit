import copy,json,tempfile,unittest
from pathlib import Path
from traceaudit.llm_infra import (ContractError,ExperimentStore,ProviderResult,assert_experiment_ready,build_input,cache_key,execute_cached,ground_response,parse_event_citations,validate_input,validate_output,withhold_single_event)
P=Path(__file__).resolve().parent

def fixtures():
    trace=json.loads((P/'fixtures/synthetic_episode.json').read_text())
    response=json.loads((P/'fixtures/synthetic_classifier_response.json').read_text())
    return trace,response

def request_and_response():
    t,r=fixtures();return build_input(t,t['task_instruction']),r

class ClassifierContractTests(unittest.TestCase):
    def test_synthetic_structured_input_and_output(self):
        req,res=request_and_response()
        self.assertTrue(validate_input(req));self.assertTrue(validate_output(res))
        self.assertEqual(len(req['events']),2)
        self.assertEqual(ground_response(req,res)['checked_citations'],1)

    def test_overlapping_events_are_allowed_if_start_ordered(self):
        req,_=request_and_response()
        self.assertGreater(req['events'][0]['indices']['frame_range'][1],req['events'][1]['indices']['frame_range'][0])
        self.assertTrue(validate_input(req))

    def test_outcome_fields_are_rejected_before_projection(self):
        trace,_=fixtures();trace['terminal_outcome']='success'
        with self.assertRaisesRegex(ContractError,'outcome/label'):
            build_input(trace,trace['task_instruction'])

    def test_reordered_or_duplicate_ids_are_rejected(self):
        req,_=request_and_response()
        reversed_request=copy.deepcopy(req);reversed_request['events'].reverse()
        with self.assertRaises(ContractError):validate_input(reversed_request)
        duplicate=copy.deepcopy(req);duplicate['events'][1]['event_id']=duplicate['events'][0]['event_id']
        with self.assertRaises(ContractError):validate_input(duplicate)

    def test_invalid_source_time_pair_is_rejected(self):
        req,_=request_and_response();req['events'][0]['timestamps']['source_values_s_unverified']=[0.7,0.2]
        with self.assertRaises(ContractError):validate_input(req)

    def test_single_event_withholding_preserves_chronology_and_timing(self):
        req,_=request_and_response();original=copy.deepcopy(req);eid=req['events'][0]['event_id']
        out=withhold_single_event(req,eid)
        self.assertEqual(req,original)
        self.assertEqual([e['event_id'] for e in out['events']],[e['event_id'] for e in req['events']])
        marker=out['events'][0]
        self.assertEqual(marker['availability'],'unavailable')
        self.assertEqual(marker['unavailable_reason'],'single_event_withholding')
        self.assertEqual(marker['timestamps'],req['events'][0]['timestamps'])
        self.assertEqual(marker['indices'],req['events'][0]['indices'])
        self.assertNotIn('event_type',marker);self.assertNotIn('measurements',marker);self.assertNotIn('evidence',marker)
        self.assertEqual(sum(e['availability']=='unavailable' for e in out['events']),1)

    def test_withholding_requires_exactly_one_available_event(self):
        req,_=request_and_response()
        with self.assertRaises(ContractError):withhold_single_event(req,'missing:EVT:9999')

    def test_citation_parser_resolves_full_and_reports_short_or_unknown_ids(self):
        req,_=request_and_response();ids=[e['event_id'] for e in req['events']]
        out=parse_event_citations(f"{ids[0]} and EVT:7777 and other-episode:EVT:8888",ids)
        self.assertEqual(out['citations'],[ids[0]])
        self.assertEqual(out['unknown_citations'],['EVT:7777','other-episode:EVT:8888'])

    def test_grounding_rejects_unknown_or_withheld_citations(self):
        req,res=request_and_response();bad=copy.deepcopy(res);bad['predictions'][0]['citations']=['unknown:EVT:0001']
        with self.assertRaisesRegex(ContractError,'unknown or withheld'):ground_response(req,bad)
        hidden=withhold_single_event(req,req['events'][0]['event_id'])
        with self.assertRaisesRegex(ContractError,'unknown or withheld'):ground_response(hidden,res)

    def test_grounding_requires_inline_citations_to_match_structured_citations(self):
        req,res=request_and_response();bad=copy.deepcopy(res)
        bad['predictions'][0]['rationale']+=' Also EVT:9999.'
        with self.assertRaisesRegex(ContractError,'unresolvable event citations'):ground_response(req,bad)
        bad['predictions'][0]['rationale']=f"This mentions {req['events'][1]['event_id']} but only another ID is structured."
        with self.assertRaisesRegex(ContractError,'not listed'):ground_response(req,bad)

    def test_abstention_is_structured_without_citations(self):
        req,_=request_and_response();resp={'schema_version':'traceaudit-classifier-output-v0.1','status':'abstain','predictions':[],'abstain_reason':'synthetic evidence unavailable'}
        self.assertTrue(validate_output(resp));self.assertTrue(ground_response(req,resp)['grounded'])

class CacheAndAccountingTests(unittest.TestCase):
    def setUp(self):
        self.req,self.res=request_and_response();self.hashes={'codebook_frozen_sha256':'c'*64,'prompt_frozen_sha256':'d'*64,'reference_lock_sha256':'e'*64,'codebook_frozen':True,'prompt_frozen':True,'reference_lock_verified':True,'explicit_authorization':True}

    def test_cache_is_content_addressed_and_accounts_query_tokens_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            store=ExperimentStore(Path(d)/'store.sqlite3');calls=[]
            kwargs=dict(provider='synthetic-provider',model='synthetic-model',prompt_sha256=self.hashes['prompt_frozen_sha256'],codebook_sha256=self.hashes['codebook_frozen_sha256'],reference_lock_sha256=self.hashes['reference_lock_sha256'],parameters={'temperature':0},codebook_frozen=True,prompt_frozen=True,reference_lock_verified=True,explicit_authorization=True)
            def fake():calls.append(1);return ProviderResult(self.res,request_tokens=9,response_tokens=4,token_count_source='provider')
            r1,a1=execute_cached(store,self.req,query_id='synthetic-query-1',call=fake,**kwargs)
            r2,a2=execute_cached(store,self.req,query_id='synthetic-query-2',call=lambda:(_ for _ in ()).throw(AssertionError('cache miss')),**kwargs)
            self.assertEqual(r1,r2);self.assertEqual(len(calls),1)
            self.assertFalse(a1['cache_hit']);self.assertTrue(a2['cache_hit'])
            summary=store.accounting_summary()
            self.assertEqual(summary['query_records'],2);self.assertEqual(summary['provider_requests'],1);self.assertEqual(summary['cache_hits'],1)
            self.assertEqual(summary['provider_request_tokens'],9);self.assertEqual(summary['provider_response_tokens'],4)
            self.assertGreaterEqual(summary['runtime_ms_total'],0)

    def test_cache_key_varies_by_codebook_prompt_and_parameters(self):
        base=dict(request=self.req,provider='p',model='m',prompt_sha256='a'*64,parameters={'temperature':0},codebook_sha256='b'*64,reference_lock_sha256='c'*64)
        k=cache_key(**base)
        self.assertNotEqual(k,cache_key(**{**base,'codebook_sha256':'c'*64}))
        self.assertNotEqual(k,cache_key(**{**base,'prompt_sha256':'d'*64}))
        self.assertNotEqual(k,cache_key(**{**base,'parameters':{'temperature':0.2}}))

    def test_execute_cached_does_not_call_provider_before_gate(self):
        with tempfile.TemporaryDirectory() as d:
            store=ExperimentStore(Path(d)/'store.sqlite3');calls=[]
            kwargs=dict(provider='synthetic-provider',model='synthetic-model',prompt_sha256='d'*64,codebook_sha256='c'*64,reference_lock_sha256='e'*64,parameters={},query_id='blocked-query',codebook_frozen=True,prompt_frozen=True,reference_lock_verified=True,explicit_authorization=False,call=lambda:(calls.append(1),ProviderResult(self.res))[1])
            with self.assertRaises(ContractError):execute_cached(store,self.req,**kwargs)
            self.assertEqual(calls,[])

    def test_real_experiment_gate_fails_closed_before_freeze_and_authorization(self):
        with self.assertRaises(ContractError):assert_experiment_ready()
        with self.assertRaises(ContractError):assert_experiment_ready(codebook_frozen_sha256='c'*64,prompt_frozen_sha256='d'*64,reference_lock_sha256='e'*64,explicit_authorization=True)
        with self.assertRaises(ContractError):assert_experiment_ready(**{**self.hashes,'explicit_authorization':False})
        self.assertTrue(assert_experiment_ready(**self.hashes))

if __name__=='__main__':unittest.main(verbosity=2)
