"""Small reference algorithms with explicit contracts and independent tests."""
from __future__ import annotations
from bisect import bisect_right
from collections import deque


def knapsack(items: list[tuple[int,int]], capacity: int) -> int:
    if capacity < 0 or any(w <= 0 for w,_ in items):
        raise ValueError("capacity nonnegative; item weights strictly positive")
    dp = [0]*(capacity+1)
    for weight,value in items:
        for c in range(capacity, weight-1, -1):
            dp[c] = max(dp[c], dp[c-weight]+value)
    return dp[-1]


def exact_knapsack(items: list[tuple[int,int]], capacity: int) -> int | None:
    if capacity < 0 or any(w <= 0 for w,_ in items):
        raise ValueError("bad capacity or weight")
    dp: list[int | None] = [None]*(capacity+1)
    dp[0] = 0
    for w,v in items:
        for c in range(capacity,w-1,-1):
            prev = dp[c-w]
            if prev is not None:
                dp[c] = prev+v if dp[c] is None else max(dp[c],prev+v)
    return dp[-1]


def intervals(jobs: list[tuple[int,int,int]]) -> tuple[int,list[int],list[int]]:
    if any(s>=e for s,e,_ in jobs):
        raise ValueError("positive duration required")
    jobs = sorted(jobs, key=lambda x:x[1])
    ends = [e for _,e,_ in jobs]
    dp,p = [0],[]
    for i,(s,_,v) in enumerate(jobs):
        j = bisect_right(ends,s,0,i)
        p.append(j)
        dp.append(max(dp[-1],v+dp[j]))
    return dp[-1],p,dp


class Flow:
    """Paired residual arcs; integer capacities; parallel arcs allowed."""
    def __init__(self,n:int):
        if n < 2: raise ValueError("need at least two vertices")
        self.adj: list[list[list[int]]] = [[] for _ in range(n)]

    def add(self,u:int,v:int,c:int) -> None:
        if not 0<=u<len(self.adj) or not 0<=v<len(self.adj) or u==v or c<0:
            raise ValueError("bad edge; self-loops omitted in this teaching model")
        self.adj[u].append([v,len(self.adj[v]),c])
        self.adj[v].append([u,len(self.adj[u])-1,0])

    def augment_path(self, vertices:list[int], amount:int=1) -> None:
        """Used only for a chosen demonstration path without parallel ambiguity."""
        path=[]
        for u,v in zip(vertices,vertices[1:]):
            candidates=[i for i,e in enumerate(self.adj[u]) if e[0]==v and e[2]>=amount]
            if not candidates or amount<=0: raise ValueError("not a residual path")
            path.append((u,candidates[0]))
        for u,i in path:
            v,rev,_=self.adj[u][i]
            self.adj[u][i][2]-=amount
            self.adj[v][rev][2]+=amount

    def maxflow(self,s:int,t:int)->int:
        if s==t or not 0<=s<len(self.adj) or not 0<=t<len(self.adj):
            raise ValueError("invalid source/sink")
        value=0
        while True:
            prev: list[tuple[int,int] | None]=[None]*len(self.adj)
            prev[s]=(-1,-1); queue=deque([s])
            while queue and prev[t] is None:
                u=queue.popleft()
                for i,(v,_,cap) in enumerate(self.adj[u]):
                    if cap>0 and prev[v] is None:
                        prev[v]=(u,i);queue.append(v)
            if prev[t] is None: return value
            path=[];v=t
            while v!=s:
                edge=prev[v];assert edge is not None
                u,i=edge;path.append((u,i));v=u
            amount=min(self.adj[u][i][2] for u,i in path)
            for u,i in path:
                v,rev,_=self.adj[u][i]
                self.adj[u][i][2]-=amount;self.adj[v][rev][2]+=amount
            value+=amount


def matching(nleft:int,nright:int,edges:list[tuple[int,int]])->int:
    f=Flow(nleft+nright+2);s=nleft+nright;t=s+1
    for u in range(nleft):f.add(s,u,1)
    for v in range(nright):f.add(nleft+v,t,1)
    for u,v in edges:f.add(u,nleft+v,1)
    return f.maxflow(s,t)
