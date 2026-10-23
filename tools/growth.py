#!/usr/bin/env python3
"""Measure the growth of the LEGAL-STATE library: how many connected+symmetric shapes fit in NxN.
This is the number that decides whether 'pre-enumerate legal states' can work at 11x11."""
import sys, time
from engine import sym_info

def count_legal(N, cap_seconds=900):
    cells=[(r,c) for r in range(N) for c in range(N)]
    idx={c:i for i,c in enumerate(cells)}
    NB=[0]*(N*N)
    for i,(r,c) in enumerate(cells):
        for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            rr,cc=r+dr,c+dc
            if 0<=rr<N and 0<=cc<N: NB[i]|=1<<idx[(rr,cc)]
    t0=time.time(); total=0; conn_total=0
    for a in range(N*N):
        if time.time()-t0>cap_seconds:
            return None, conn_total, time.time()-t0
        seen={1<<a}; stack=[1<<a]
        while stack:
            S=stack.pop()
            m=S; cand=0
            while m:
                b=m&-m; m-=b; cand|=NB[b.bit_length()-1]
            cand&=~S
            for i in range(a+1, N*N):
                if (cand>>i)&1:
                    T=S|(1<<i)
                    if T not in seen: seen.add(T); stack.append(T)
        conn_total+=len(seen)
        for S in seen:
            cl=[cells[i] for i in range(N*N) if (S>>i)&1]
            cap0,names,fixes,fs=sym_info(cl)
            if names: total+=1
    return total, conn_total, time.time()-t0

if __name__=="__main__":
    for N in (4,5,6):
        t,conn,dt=count_legal(N)
        if t is None:
            print(f"  N={N}: TIMEOUT after {dt:.0f}s (connected subsets so far ~{conn:,})", flush=True); break
        print(f"  N={N}: connected subsets={conn:,}  legal states={t:,}  ({dt:.0f}s)", flush=True)
