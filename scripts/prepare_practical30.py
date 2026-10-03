"""Freeze new executable operations/code canaries before asking any model.

These original function tasks are a local diagnostic, not SWE-bench or full-size parity.
Only positive/negative controls run in the isolated grader; the model sees no controls.
"""
import hashlib
import json
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from practical_cases import program

CASES = []


def case(name, signature, specification, examples, control):
    arguments, expected = examples[0]
    visible_example = ' Example: solve(' + ', '.join(repr(v) for v in arguments) + ') returns ' + repr(expected) + '.'
    CASES.append(program(name, f'Implement solve({signature}) in Python using only the standard library. '
        + specification + visible_example + ' Return only the complete implementation in a Python code block.',
        examples[:1], examples[1:], textwrap.dedent(control)))


case('merge-patch', 'target, patch',
    'Apply JSON Merge Patch: a non-object patch replaces the target; an object patch treats a non-object '
    'target as an empty object. Null-valued object members delete that key; other members are recursively '
    'patched. Return the resulting JSON value.',
    [([{'a':1,'b':2},{'a':None,'c':3}],{'b':2,'c':3}),
     ([{'a':{'b':1,'c':2}},{'a':{'b':None}}],{'a':{'c':2}}),
     ([[1,2],{'x':3}],{'x':3}), ([{'a':1},[3]], [3]), ([1,None],None),
     ([{}, {'a':{'b':None,'c':[]}}],{'a':{'c':[]}})], r'''
    import copy
    def solve(target,patch):
        if not isinstance(patch,dict): return copy.deepcopy(patch)
        result=copy.deepcopy(target) if isinstance(target,dict) else {}
        for k,v in patch.items():
            if v is None: result.pop(k,None)
            else: result[k]=solve(result.get(k),v)
        return result
    ''')

case('json-pointer', 'document, pointer',
    'Resolve a JSON Pointer. Empty pointer selects the whole document. Other pointers must start with /. '
    'Decode ~1 as / and ~0 as ~; any other ~ escape is invalid. For arrays accept only 0 or a positive '
    'decimal index without leading zeros, within bounds. Dictionary keys are exact strings. '
    'Return {"found":true,"value":value} on success or {"found":false} on invalid/missing paths.',
    [([{'a':[7,None]},'/a/1'],{'found':True,'value':None}),
     ([{'a/b':{'~':4}},'/a~1b/~0'],{'found':True,'value':4}),
     ([[4],'/01'],{'found':False}), ([[4],'/-'],{'found':False}),
     ([{'':2},'/'],{'found':True,'value':2}), ([3,''],{'found':True,'value':3}),
     ([{'x':1},'/x~2'],{'found':False}), ([[],'/0'],{'found':False})], r'''
    import re
    def solve(document,pointer):
        if pointer=='': return {'found':True,'value':document}
        if not isinstance(pointer,str) or not pointer.startswith('/'): return {'found':False}
        current=document
        for token in pointer[1:].split('/'):
            if re.search(r'~(?![01])',token): return {'found':False}
            token=token.replace('~1','/').replace('~0','~')
            if isinstance(current,dict) and token in current: current=current[token]
            elif isinstance(current,list) and re.fullmatch(r'0|[1-9][0-9]*',token) and int(token)<len(current): current=current[int(token)]
            else: return {'found':False}
        return {'found':True,'value':current}
    ''')

case('environment-expansion', 'text, variables',
    'Expand ${NAME} for names matching [A-Za-z_][A-Za-z0-9_]* from a string-valued variables dictionary. '
    '$$ becomes a literal $, processed without further expansion. Missing valid variables return None. '
    'Other $ forms stay literal. A replacement is not recursively expanded.',
    [(['${HOST}:$$${PORT}',{'HOST':'db','PORT':'5432'}],'db:$5432'),
     (['$HOME ${MISSING}',{}],None), (['$${HOST}',{'HOST':'db'}],'${HOST}'),
     (['${X}',{'X':'${Y}','Y':'ok'}],'${Y}'), (['${9bad} $x',{}],'${9bad} $x'), (['plain',{}],'plain')], r'''
    import re
    def solve(text,variables):
        missing=False
        def sub(m):
            nonlocal missing
            if m[0]=='$$': return '$'
            if m[1] not in variables: missing=True; return ''
            return variables[m[1]]
        result=re.sub(r'\$\$|\$\{([A-Za-z_][A-Za-z0-9_]*)\}',sub,text)
        return None if missing else result
    ''')

case('sandbox-path', 'path',
    'Normalize a POSIX relative path within a sandbox, lexically without filesystem access. Reject absolute '
    'paths, NUL characters, or any .. component that would go above the sandbox, returning None. Ignore empty and . '
    'components; backslashes are ordinary characters. Return normalized relative text, using . for the root.',
    [(['a/./b/../c'],'a/c'), (['../a'],None), (['a/../../b'],None),
     (['/etc'],None), (['a//b/'],'a/b'), (['a/..'],'.'), ([''],'.'), (['a\u0000b'],None)], r'''
    def solve(path):
        if path.startswith('/') or '\0' in path: return None
        stack=[]
        for part in path.split('/'):
            if part in ('','.'): continue
            if part=='..':
                if not stack: return None
                stack.pop()
            else: stack.append(part)
        return '/'.join(stack) or '.'
    ''')

case('numeric-version-sort', 'versions',
    'Keep only strings matching an optional lowercase v followed by three nonnegative dot-separated integer '
    'components. Leading zeros are allowed. Sort numerically by the three components, stably for equal '
    'versions, and return the original strings. Ignore malformed strings.',
    [([['1.10.0','1.2.0','v2.0.0']],['1.2.0','1.10.0','v2.0.0']),
     ([['v01.2.3','1.02.3','1.2','1.2.3-rc1']],['v01.2.3','1.02.3']),
     ([['0.0.0','v0.0.0','V1.0.0','-1.0.0','1.0.0 ']],['0.0.0','v0.0.0']), ([[]],[])], r'''
    import re
    def solve(versions):
        good=[v for v in versions if isinstance(v,str) and re.fullmatch(r'v?[0-9]+\.[0-9]+\.[0-9]+',v)]
        return sorted(good,key=lambda v:tuple(map(int,v.removeprefix('v').split('.'))))
    ''')

case('dependency-order', 'dependencies',
    'The dictionary maps node names to lists of prerequisite node names. Include nodes appearing only as '
    'prerequisites. Return a topological ordering, choosing the lexicographically smallest currently ready '
    'node at every step. Duplicate edges are ignored. Return None if there is a cycle.',
    [([{'web':['db'],'db':[]}],['db','web']),
     ([{'a':['z'],'b':[]}],['b','z','a']), ([{'a':['b'],'b':['a']}],None),
     ([{'x':['x']}],None), ([{'a':['b','b']}],['b','a']), ([{}],[])], r'''
    import heapq
    def solve(dependencies):
        deps={k:set(v) for k,v in dependencies.items()}
        nodes=set(deps)|{n for v in deps.values() for n in v}
        indegree={n:len(deps.get(n,set())) for n in nodes}
        reverse={n:[] for n in nodes}
        for n,values in deps.items():
            for v in values: reverse[v].append(n)
        ready=[n for n in nodes if indegree[n]==0]; heapq.heapify(ready); out=[]
        while ready:
            n=heapq.heappop(ready); out.append(n)
            for child in reverse[n]:
                indegree[child]-=1
                if indegree[child]==0: heapq.heappush(ready,child)
        return out if len(out)==len(nodes) else None
    ''')

case('dependency-impact', 'dependencies, changed',
    'Return sorted unique changed service names plus every direct or transitive dependent. Dictionary values '
    'are prerequisite lists. Unknown changed names are retained. Cycles must terminate.',
    [([{'web':['db'],'api':['web']},['db']],['api','db','web']),
     ([{'a':['b'],'b':['a']},['a']],['a','b']), ([{'a':['b']},['x','x']],['x']),
     ([{'a':['b']},[]],[]), ([{'a':['b'],'c':['b'],'d':['c']},['b']],['a','b','c','d'])], r'''
    def solve(dependencies,changed):
        reverse={}
        for child,deps in dependencies.items():
            for parent in deps: reverse.setdefault(parent,set()).add(child)
        seen=set(changed); todo=list(seen)
        while todo:
            for child in reverse.get(todo.pop(),()):
                if child not in seen: seen.add(child); todo.append(child)
        return sorted(seen)
    ''')

case('first-fit-capacity', 'sizes, capacity',
    'Use first-fit bin packing in input order. Each item goes in the earliest existing bin where it fits, '
    'otherwise opens a bin. Return lists of item sizes per bin. Capacity and sizes must be positive integers '
    '(bool is invalid); any oversized or invalid item returns None.',
    [([[6,4,5,5],10],[[6,4],[5,5]]), ([[4,4,2,2],6],[[4,2],[4,2]]),
     ([[],5],[]), ([[7],6],None), ([[True],6],None), ([[0],6],None), ([[1],0],None)], r'''
    def solve(sizes,capacity):
        if type(capacity) is not int or capacity<=0: return None
        bins=[]; used=[]
        for size in sizes:
            if type(size) is not int or not 0<size<=capacity: return None
            for i in range(len(bins)):
                if used[i]+size<=capacity: bins[i].append(size); used[i]+=size; break
            else: bins.append([size]); used.append(size)
        return bins
    ''')

case('rollout-rounding', 'replicas, unavailable, surge',
    'Convert two nonnegative integer counts or integer-percent strings (0% through 100%) to rollout limits. '
    'Percentage unavailable rounds down and percentage surge rounds up. Integers stay unchanged, even above '
    'replicas. Replicas is a nonnegative integer. Reject bools, malformed values, or negative counts with None. '
    'Return {"unavailable":count,"surge":count}.',
    [([3,'25%','25%'],{'unavailable':0,'surge':1}),
     ([7,'30%','30%'],{'unavailable':2,'surge':3}), ([0,'100%','100%'],{'unavailable':0,'surge':0}),
     ([3,5,0],{'unavailable':5,'surge':0}), ([3,'101%',1],None), ([True,0,1],None), ([3,-1,1],None)], r'''
    import re
    def solve(replicas,unavailable,surge):
        if type(replicas) is not int or replicas<0: return None
        def parse(value,ceil):
            if type(value) is int: return value if value>=0 else None
            if not isinstance(value,str) or not re.fullmatch(r'[0-9]+%',value): return None
            p=int(value[:-1])
            if p>100: return None
            return (replicas*p+(99 if ceil else 0))//100
        a,b=parse(unavailable,False),parse(surge,True)
        return {'unavailable':a,'surge':b} if a is not None and b is not None else None
    ''')

case('path-route', 'path, routes',
    'Routes are [prefix, backend] pairs with normalized absolute prefixes, with no trailing slash except /. '
    'Select the longest prefix matching either the entire path or a boundary followed by /. Root / matches '
    'all absolute paths. Ties use the first route. Do not normalize/decode the path. Return the backend or None.',
    [(['/api/v1/x',[['/','root'],['/api','api'],['/api/v1','v1']]],'v1'),
     (['/apix',[['/api','api']]],None), (['/api',[['/api','a'],['/api','b']]],'a'),
     (['/api/',[['/api','api']]],'api'), (['relative',[['/','root']]],None), (['/',[['/','root']]],'root')], r'''
    def solve(path,routes):
        best=None; length=-1
        for prefix,backend in routes:
            match=(path.startswith('/') if prefix=='/' else path==prefix or path.startswith(prefix+'/'))
            if match and len(prefix)>length: best=backend; length=len(prefix)
        return best
    ''')


case('journal-priority', 'entries, ceiling',
    'Return MESSAGE strings from entries whose PRIORITY is exactly one ASCII digit string 0 through 7 or an integer 0 '
    'through 7, and is <= ceiling. Ignore bool priorities, missing fields and non-string messages; '
    'retain input order.',
    [([[{'PRIORITY':'3','MESSAGE':'error'},{'PRIORITY':'6','MESSAGE':'info'}],3],['error']),
     ([[{'PRIORITY':0,'MESSAGE':'panic'},{'PRIORITY':True,'MESSAGE':'bad'}],7],['panic']),
     ([[{'PRIORITY':'03','MESSAGE':'leading'},{'PRIORITY':'8','MESSAGE':'bad'}],7],[]),
     ([[{'PRIORITY':2},{'PRIORITY':2,'MESSAGE':4}],7],[]), ([[],3],[])], r'''
    def solve(entries,ceiling):
        out=[]
        for row in entries:
            p=row.get('PRIORITY')
            if isinstance(p,str) and len(p)==1 and p in '01234567': p=int(p)
            if type(p) is int and 0<=p<=7 and p<=ceiling and isinstance(row.get('MESSAGE'),str): out.append(row['MESSAGE'])
        return out
    ''')

case('nearest-rank-percentile', 'values, percent',
    'Values are finite numbers. Return the nearest-rank percentile: sort, use index ceil(percent*n/100)-1, '
    'clamped to 0 for percent=0. Empty input or percent outside [0,100] returns None.',
    [([[4,1,9,2],50],2), ([[4,1,9,2],95],9), ([[4,1,9,2],0],1),
     ([[5],33],5), ([[],90],None), ([[1,2],-1],None), ([[1,2],101],None)], r'''
    import math
    def solve(values,percent):
        if not values or not 0<=percent<=100: return None
        return sorted(values)[max(0,math.ceil(percent*len(values)/100)-1)]
    ''')

case('counter-reset-rate', 'samples',
    'Samples are [integer_timestamp, nonnegative_counter] pairs. Return the average increase per second '
    'across the whole interval. Sum adjacent increases; a decrease means a reset, contributing the new '
    'counter value. Fewer than two samples or timestamps that are not strictly increasing return None.',
    [([[[0,10],[10,30]]],2.0), ([[[0,10],[5,3],[10,13]]],1.3),
     ([[[0,5],[2,5],[4,0],[6,6]]],1.0), ([[[1,2],[1,4]]],None), ([[]],None), ([[[1,3]]],None)], r'''
    def solve(samples):
        if len(samples)<2: return None
        total=0
        for (a,x),(b,y) in zip(samples,samples[1:]):
            if b<=a: return None
            total+=y-x if y>=x else y
        return total/(samples[-1][0]-samples[0][0])
    ''')

case('latest-alert', 'events',
    'Each event has string fingerprint and numeric timestamp. Keep the event with largest timestamp per '
    'fingerprint; ties use the later input event. Return retained complete events sorted by fingerprint.',
    [([[{'fingerprint':'b','timestamp':2},{'fingerprint':'a','timestamp':1}]],
      [{'fingerprint':'a','timestamp':1},{'fingerprint':'b','timestamp':2}]),
     ([[{'fingerprint':'x','timestamp':3,'v':1},{'fingerprint':'x','timestamp':2,'v':2}]],
      [{'fingerprint':'x','timestamp':3,'v':1}]),
     ([[{'fingerprint':'x','timestamp':3,'v':1},{'fingerprint':'x','timestamp':3,'v':2}]],
      [{'fingerprint':'x','timestamp':3,'v':2}]), ([[]],[])], r'''
    def solve(events):
        latest={}
        for e in events:
            k=e['fingerprint']
            if k not in latest or e['timestamp']>=latest[k]['timestamp']: latest[k]=e
        return [latest[k] for k in sorted(latest)]
    ''')

case('expiry-cache', 'operations',
    'Simulate an initially empty cache. Operations are [time,"put",key,value,ttl] or [time,"get",key], '
    'in nondecreasing time order. Put replaces the value and expires at time+ttl (ttl is nonnegative). '
    'An entry is expired at exactly its expiry time. Return get results in order, using None for misses.',
    [([[[0,'put','a',7,5],[4,'get','a'],[5,'get','a']]], [7,None]),
     ([[[0,'put','a',1,2],[1,'put','a',2,4],[2,'get','a'],[5,'get','a']]], [2,None]),
     ([[[0,'put','x',False,3],[0,'get','x'],[1,'get','y']]], [False,None]),
     ([[[0,'put','x',9,0],[0,'get','x']]], [None]), ([[]],[])], r'''
    def solve(operations):
        cache={}; out=[]
        for op in operations:
            t,action,key=op[:3]
            if action=='put': cache[key]=(op[3],t+op[4])
            else:
                value,expires=cache.get(key,(None,t))
                out.append(value if t<expires else None)
        return out
    ''')

case('token-bucket', 'capacity, refill, requests',
    'Simulate a full token bucket at time 0. Refill is tokens per second. Requests are [time,cost] pairs '
    'in nondecreasing nonnegative time order; costs are nonnegative. Refill before each request, capped at '
    'capacity; accept and deduct only if cost fits. Return booleans for all requests.',
    [([5,1,[[0,3],[0,3],[1,3],[1,1]]],[True,False,True,False]),
     ([2,0,[[0,2],[5,1]]],[True,False]), ([3,2,[[0,3],[10,4],[10,3]]],[True,False,True]),
     ([0,3,[[0,0],[3,1]]],[True,False]), ([5,1,[]],[])], r'''
    def solve(capacity,refill,requests):
        tokens=capacity; previous=0; out=[]
        for time,cost in requests:
            tokens=min(capacity,tokens+(time-previous)*refill); previous=time
            accepted=cost<=tokens; out.append(accepted)
            if accepted: tokens-=cost
        return out
    ''')

case('backoff', 'base, maximum, attempts',
    'Attempts is a list of nonnegative integers. Return exponential retry delays min(maximum, base*2**attempt) '
    'for each element. Base and maximum are nonnegative integers. Handle very large attempts without constructing '
    'unbounded-size integers. Retain attempt order.',
    [([3,20,[0,1,2,3,4]],[3,6,12,20,20]), ([0,100,[0,1000000000]],[0,0]),
     ([1,0,[0,3]],[0,0]), ([8,3,[0,1]],[3,3]), ([1,8,[2,3,1000000000]],[4,8,8])], r'''
    def solve(base,maximum,attempts):
        if base==0 or maximum==0: return [0]*len(attempts)
        bound=maximum.bit_length()
        return [maximum if a>=bound else min(maximum,base*(1<<a)) for a in attempts]
    ''')

case('idempotency-conflicts', 'events',
    'Each event has string id and JSON payload. Keep the first event for each id, in first-seen order. '
    'Subsequent equal payloads are duplicates; different payloads mark that id as conflicted. Return '
    '{"events":first_events,"conflicts":sorted_unique_conflicted_ids}. Payloads use JSON structural '
    'equality; this task has no bool/number equality edge cases.',
    [([[{'id':'x','payload':1},{'id':'x','payload':1}]],{'events':[{'id':'x','payload':1}],'conflicts':[]}),
     ([[{'id':'b','payload':1},{'id':'a','payload':2},{'id':'b','payload':3}]],
      {'events':[{'id':'b','payload':1},{'id':'a','payload':2}],'conflicts':['b']}),
     ([[{'id':'x','payload':{'a':1,'b':2}},{'id':'x','payload':{'b':2,'a':1}}]],
      {'events':[{'id':'x','payload':{'a':1,'b':2}}],'conflicts':[]}),
     ([[]],{'events':[],'conflicts':[]})], r'''
    def solve(events):
        seen={}; conflicts=set()
        for event in events:
            k=event['id']
            if k not in seen: seen[k]=event
            elif seen[k]['payload']!=event['payload']: conflicts.add(k)
        return {'events':list(seen.values()),'conflicts':sorted(conflicts)}
    ''')

case('memory-info', 'text',
    'Parse lines of the exact form NAME: nonnegative_integer kB, with optional outer whitespace. '
    'Last valid occurrence wins. Return available bytes using MemAvailable if present, otherwise the sum '
    'of MemFree, Buffers, Cached (missing fields count as zero). kB means 1024 bytes. Ignore malformed lines.',
    [(['MemAvailable: 12 kB\nMemFree: 5 kB\n'],12288),
     (['MemFree: 3 kB\nBuffers: 2 kB\nCached: 4 kB'],9216),
     (['MemAvailable: 0 kB\nCached: 4 kB'],0), (['MemFree: 5 kB\nMemFree: 2 kB'],2048),
     (['MemFree: -2 kB\nCached: 4 MB\nwrong'],0)], r'''
    import re
    def solve(text):
        values={}
        for line in text.splitlines():
            match=re.fullmatch(r'\s*([A-Za-z_]+):\s*([0-9]+)\s+kB\s*',line)
            if match: values[match[1]]=int(match[2])
        n=values.get('MemAvailable',sum(values.get(k,0) for k in ('MemFree','Buffers','Cached')))
        return n*1024
    ''')

case('cgroup-quota', 'text',
    'Parse cgroup CPU quota text as two whitespace-separated fields, quota and period. Quota max returns '
    'None; otherwise both fields must contain only decimal digits and be positive. Return ceil(1000*quota/period) '
    'millicores, or None for malformed/zero/negative values.',
    [(['150000 100000'],1500), (['1 3'],334), (['max 100000'],None),
     (['0 100'],None), (['-1 100'],None), (['2 0'],None), (['2 3 extra'],None), (['  3\t2\n'],1500)], r'''
    def solve(text):
        fields=text.split()
        if len(fields)!=2 or not all(x.isascii() and x.isdigit() for x in fields): return None
        quota,period=map(int,fields)
        if quota<=0 or period<=0: return None
        return (1000*quota+period-1)//period
    ''')


case('canonical-query', 'pairs',
    'Pairs are [string_key,string_value]. Sort lexicographically by key then value, retaining duplicates. '
    'Return a URL query string, UTF-8 percent encoding each component, with only ASCII letters, digits, '
    'and -._~ unescaped. Spaces are %20, never +. Empty input returns an empty string.',
    [([[['b','2'],['a','x y']]],'a=x%20y&b=2'),
     ([[['x','+'],['x','&'],['x','+']]],'x=%26&x=%2B&x=%2B'),
     ([[['é','/']]],'%C3%A9=%2F'), ([[['','']]],'='), ([[]],'')], r'''
    from urllib.parse import quote
    def solve(pairs):
        return '&'.join(quote(k,safe='-._~')+'='+quote(v,safe='-._~') for k,v in sorted(pairs))
    ''')

case('duration-milliseconds', 'text',
    'Parse a nonnegative plain decimal duration followed by ms, s, min or h (case-sensitive). Allow outer '
    'and number/unit whitespace. Digits are required before and after any decimal point. Return an integer '
    'millisecond count, or None for invalid/non-integral values. Reject signs, exponents and missing units.',
    [(['1.5 s'],1500), (['0.1 ms'],None), (['2 min'],120000), (['0.25h'],900000),
     (['-1s'],None), (['1e3ms'],None), (['.5s'],None), (['3'],None), (['  0 ms  '],0)], r'''
    import re
    from decimal import Decimal
    def solve(text):
        m=re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|s|min|h)\s*',text)
        if not m: return None
        value=Decimal(m[1])*{'ms':1,'s':1000,'min':60000,'h':3600000}[m[2]]
        return int(value) if value==value.to_integral_value() else None
    ''')

case('literal-endpoint', 'text',
    'Parse an IPv4 literal:port or [IPv6 literal]:port, with no whitespace or zone identifier. IPv6 '
    'must be bracketed. Port is decimal digits in [1,65535]. Return {"address":canonical_IP,"port":integer}, '
    'or None on invalid input. Never resolve hostnames.',
    [(['127.0.0.1:8080'],{'address':'127.0.0.1','port':8080}),
     (['[2001:0db8::1]:443'],{'address':'2001:db8::1','port':443}),
     (['::1:80'],None), (['localhost:80'],None), (['[fe80::1%eth0]:80'],None),
     (['0.0.0.0:0'],None), (['1.2.3.4:65536'],None), (['1.2.3.4:080'],{'address':'1.2.3.4','port':80})], r'''
    import ipaddress,re
    def solve(text):
        m=re.fullmatch(r'(?:\[([^\]]+)\]|([^:\s]+)):([0-9]+)',text)
        if not m or '%' in text: return None
        try: address=ipaddress.ip_address(m[1] or m[2])
        except ValueError: return None
        if (m[1] is not None)!=(address.version==6): return None
        port=int(m[3])
        return {'address':str(address),'port':port} if 1<=port<=65535 else None
    ''')

case('retry-after', 'header, now',
    'Return retry delay seconds. Header after outer whitespace is either nonnegative decimal integer seconds '
    'or an HTTP date exactly in the format Wed, 21 Oct 2015 07:28:00 GMT. Parse dates in UTC; now is integer '
    'Unix time. Past dates return 0. Invalid headers return None; ignore correctness of the weekday label.',
    [(['120',0],120), ([' Thu, 01 Jan 1970 00:00:10 GMT ',3],7),
     (['Thu, 01 Jan 1970 00:00:10 GMT',15],0), (['-1',0],None),
     (['1.5',0],None), (['Thu, 01 Jan 1970 00:00:10 UTC',0],None), ([' 0003 ',0],3)], r'''
    import datetime,re
    def solve(header,now):
        text=header.strip()
        if re.fullmatch(r'[0-9]+',text): return int(text)
        if not re.fullmatch(r'[A-Za-z]{3}, [0-9]{2} [A-Za-z]{3} [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT',text): return None
        try: date=datetime.datetime.strptime(text,'%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=datetime.timezone.utc)
        except ValueError: return None
        return max(0,int(date.timestamp())-now)
    ''')

case('access-log-summary', 'lines',
    'Parse a simplified access log line: non-whitespace peer, one space, a quoted request without quotes, '
    'one space, three-digit status, one space, decimal byte count or -. Status must be 100 through 599. '
    'Ignore malformed lines. Return {"requests":count,"bytes":sum,"statuses":map_of_string_status_to_count}. '
    'A - byte count contributes zero.',
    [([['x "GET / HTTP/1.1" 200 10','x "GET /x HTTP/1.1" 404 -']],
      {'requests':2,'bytes':10,'statuses':{'200':1,'404':1}}),
     ([['x "" 500 20','x "GET /" 500 2','malformed','x "GET /" 999 3']],
      {'requests':2,'bytes':22,'statuses':{'500':2}}),
     ([['x "GET /" 200 -2','x "GET /" 20 3']],{'requests':0,'bytes':0,'statuses':{}}),
     ([[]],{'requests':0,'bytes':0,'statuses':{}})], r'''
    import re
    def solve(lines):
        result={'requests':0,'bytes':0,'statuses':{}}
        for line in lines:
            m=re.fullmatch(r'\S+ "[^"\n]*" ([0-9]{3}) ([0-9]+|-)',line)
            if not m or not 100<=int(m[1])<=599: continue
            result['requests']+=1; result['bytes']+=0 if m[2]=='-' else int(m[2])
            result['statuses'][m[1]]=result['statuses'].get(m[1],0)+1
        return result
    ''')

case('unit-dependencies', 'text',
    'Within every [Unit] section of a simplified unit file, collect After and Wants values split on whitespace. '
    'Ignore other sections/keys, blank lines and full-line # or ; comments. An empty assignment resets that '
    'directive. Return {"After":list,"Wants":list}, retaining first occurrence order without duplicates. '
    'Strip outer whitespace; no continuations or inline comments are present.',
    [(['[Unit]\nAfter=network.target db.service\nWants=db.service\n'],
      {'After':['network.target','db.service'],'Wants':['db.service']}),
     (['[Unit]\nAfter=a b\nAfter=\nAfter=c c\n[Service]\nWants=x'],{'After':['c'],'Wants':[]}),
     (['# comment\n[Unit]\nWants=x y\n[Other]\nAfter=z\n[Unit]\nWants=y z'],
      {'After':[],'Wants':['x','y','z']}), ([''],{'After':[],'Wants':[]})], r'''
    def solve(text):
        result={'After':[],'Wants':[]}; section=''
        for raw in text.splitlines():
            line=raw.strip()
            if not line or line.startswith(('#',';')): continue
            if line.startswith('[') and line.endswith(']'): section=line[1:-1]; continue
            if section!='Unit' or '=' not in line: continue
            key,value=line.split('=',1); key=key.strip(); value=value.strip()
            if key not in result: continue
            if not value: result[key]=[]
            else:
                for item in value.split():
                    if item not in result[key]: result[key].append(item)
        return result
    ''')

case('interval-union', 'intervals',
    'Intervals are [start,end] integer pairs representing half-open windows. Drop intervals with end<=start. '
    'Merge overlapping or touching intervals; return sorted merged pairs. Input may be unsorted and contain duplicates.',
    [([[[5,8],[1,3],[3,5]]],[[1,8]]), ([[[1,2],[4,5],[2,1],[3,3]]],[[1,2],[4,5]]),
     ([[[-3,0],[-1,2],[2,4]]],[[-3,4]]), ([[[1,3],[1,3],[2,3]]],[[1,3]]), ([[]],[])], r'''
    def solve(intervals):
        out=[]
        for start,end in sorted((a,b) for a,b in intervals if b>a):
            if out and start<=out[-1][1]: out[-1][1]=max(end,out[-1][1])
            else: out.append([start,end])
        return out
    ''')

case('dns-wildcard', 'hostname, patterns',
    'Return whether a hostname matches an exact DNS name or wildcard pattern *.example.com. Case-insensitive; '
    'remove one optional trailing dot from names/patterns. A wildcard matches exactly one nonempty label, '
    'never the bare suffix or multiple labels. Other asterisks are invalid and ignored.',
    [(['API.Example.Com.',['*.example.com']],True), (['example.com',['*.example.com']],False),
     (['x.y.example.com',['*.example.com']],False), (['x.example.com',['x.example.com.']],True),
     (['foo',['f*']],False), (['.example.com',['*.example.com']],False), (['x',[]],False)], r'''
    def solve(hostname,patterns):
        host=hostname.lower().removesuffix('.')
        for pattern in patterns:
            p=pattern.lower().removesuffix('.')
            if '*' not in p and host==p: return True
            if p.startswith('*.') and p.count('*')==1:
                suffix=p[1:]
                if host.endswith(suffix):
                    prefix=host[:-len(suffix)]
                    if prefix and '.' not in prefix: return True
        return False
    ''')

case('log-rotation-plan', 'names, base, keep',
    'Return names to delete under a simple rotation policy. Recognize only base.NUM where NUM is a positive '
    'integer without leading zeros, optionally followed by .gz. Keep NUM<=keep and delete NUM>keep. Ignore '
    'unrecognized names. Return sorted unique deletion names; keep is a nonnegative integer.',
    [([['app.log','app.log.1','app.log.2.gz','app.log.3'],'app.log',1],['app.log.2.gz','app.log.3']),
     ([['a.01','a.0','a.1.gz','a.1.gz','a.3.bak'],'a',0],['a.1.gz']),
     ([['aXlog.2','a.log.2'],'a.log',1],['a.log.2']), ([[],'x',3],[])], r'''
    import re
    def solve(names,base,keep):
        regex=re.compile(re.escape(base)+r'\.([1-9][0-9]*)(?:\.gz)?')
        return sorted({name for name in names if (m:=regex.fullmatch(name)) and int(m[1])>keep})
    ''')

case('typed-json-equality', 'left, right',
    'Compare JSON values structurally. Object key order is irrelevant; arrays are ordered. Booleans are '
    'distinct from numbers (true differs from 1). Integer and floating-point numbers compare numerically '
    '(1 equals 1.0). All other JSON types must match. Return a boolean.',
    [([True,1],False), ([1,1.0],True), ([{'a':True},{'a':1}],False),
     ([{'b':2,'a':[1,None]},{'a':[1.0,None],'b':2}],True), ([[1,2],[2,1]],False),
     ([None,False],False), (['1',1],False), ([{},[]],False)], r'''
    def solve(left,right):
        if type(left) in (int,float) and type(right) in (int,float): return left==right
        if type(left) is not type(right): return False
        if isinstance(left,dict): return left.keys()==right.keys() and all(solve(left[k],right[k]) for k in left)
        if isinstance(left,list): return len(left)==len(right) and all(solve(a,b) for a,b in zip(left,right))
        return left==right
    ''')


def main():
    if len(CASES) != 30 or len({c['id'] for c in CASES}) != 30:
        raise RuntimeError('Expected exactly 30 unique new canaries')
    out = ROOT/'eval/practical30-v2-cases.jsonl'
    data = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in CASES)
    if out.exists() and out.read_text() != data:
        raise RuntimeError('Refuse to overwrite a different frozen deck')
    out.parent.mkdir(exist_ok=True)
    out.write_text(data)
    manifest = {'scope': '30 original executable DevOps/SysAdmin/Python function canaries; '
                         'not an external benchmark or repository repair qualification.',
                'protocol_version': 2,
                'revision_reason': 'Q4 prototype audit identified three ambiguous interfaces. Specify rejection '
                    'return value, single-digit priorities and list-valued attempts; expose the first public '
                    'example in every prompt. All 30 are rerun; no private tests or reference controls changed. '
                    'This revised prompt deck is not a blind preregistered evaluation.',
                'cases_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'case_ids': [c['id'] for c in CASES],
                'selection': 'Revised prompts frozen before v2 responses; manually specified tests unchanged. '
                             'Model receives prompt and one public example, never reference controls or private tests.'}
    prototype = ROOT/'eval/practical30-cases.jsonl'
    if prototype.exists():
        before = [json.loads(line) for line in prototype.read_text().splitlines()]
        if [{k:v for k,v in c.items() if k!='prompt'} for c in before] != [
                {k:v for k,v in c.items() if k!='prompt'} for c in CASES]:
            raise RuntimeError('V2 must not change prototype grading payloads or controls')
        manifest['prototype_cases_sha256'] = hashlib.sha256(prototype.read_bytes()).hexdigest()
    (ROOT/'results/practical30-v2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(manifest)


if __name__ == '__main__':
    main()
