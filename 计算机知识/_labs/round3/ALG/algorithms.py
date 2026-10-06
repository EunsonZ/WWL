from collections import deque
import itertools,random

def maxflow(cap,s,t):
    if s==t:raise ValueError("distinct source and sink required")
    n=len(cap);r=[row[:] for row in cap];total=0
    while True:
        parent=[-1]*n;parent[s]=s;q=deque([s])
        while q and parent[t]<0:
            u=q.popleft()
            for v in range(n):
                if r[u][v]>0 and parent[v]<0:parent[v]=u;q.append(v)
        if parent[t]<0:break
        amount=float('inf');v=t
        while v!=s:u=parent[v];amount=min(amount,r[u][v]);v=u
        v=t
        while v!=s:u=parent[v];r[u][v]-=amount;r[v][u]+=amount;v=u
        total+=amount
    return total

def knapsack(items,capacity):
    dp=[0]*(capacity+1)
    for weight,value in items:
        for c in range(capacity,weight-1,-1):dp[c]=max(dp[c],dp[c-weight]+value)
    return dp[-1]

def main():
    rng=random.Random(20260906)
    for _ in range(100):
        n=5;cap=[[0 if i==j else rng.randrange(4) for j in range(n)] for i in range(n)]
        cuts=[]
        for bits in itertools.product((False,True),repeat=n-2):
            left={0}|{i+1 for i,b in enumerate(bits) if b}
            cuts.append(sum(cap[i][j] for i in left for j in range(n) if j not in left))
        assert maxflow(cap,0,n-1)==min(cuts)
    for _ in range(100):
        items=[(rng.randrange(1,7),rng.randrange(1,20)) for _ in range(8)];c=12
        brute=max(sum(v for (w,v),b in zip(items,bits) if b) for bits in itertools.product((0,1),repeat=8) if sum(w for (w,v),b in zip(items,bits) if b)<=c)
        assert knapsack(items,c)==brute
    assert knapsack([(2,3)],4)==3 # ascending loop would incorrectly return 6
    print("PASS: 100 maxflow/mincut certificates + 100 knapsack/brute-force comparisons")
if __name__=='__main__':main()
