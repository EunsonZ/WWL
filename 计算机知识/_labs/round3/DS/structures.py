import random
class Fenwick:
    def __init__(self,n):
        if type(n) is not int or n<0:raise ValueError("size")
        self.n=n;self.bit=[0]*(n+1)
    def add(self,index,delta):
        if not 0<=index<self.n:raise IndexError(index)
        i=index+1
        while i<=self.n:self.bit[i]+=delta;i+=i&-i
    def prefix(self,end):
        if not 0<=end<=self.n:raise IndexError(end)
        s=0;i=end
        while i:s+=self.bit[i];i-=i&-i
        return s
class DSU:
    def __init__(self,n):self.p=list(range(n));self.sz=[1]*n
    def find(self,x):
        while self.p[x]!=x:self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a==b:return False
        if self.sz[a]<self.sz[b]:a,b=b,a
        self.p[b]=a;self.sz[a]+=self.sz[b];return True

def main():
    rng=random.Random(20260906);a=[0]*31;f=Fenwick(len(a))
    for _ in range(1000):
        i=rng.randrange(len(a));d=rng.randrange(-100,101);a[i]+=d;f.add(i,d)
        for end in range(len(a)+1):assert f.prefix(end)==sum(a[:end])
    for bad in (-1,31):
        try:f.add(bad,1)
        except IndexError:pass
        else:raise AssertionError("bounds")
    d=DSU(20);sets=[{i} for i in range(20)]
    for _ in range(200):
        a,b=rng.randrange(20),rng.randrange(20)
        sa=next(s for s in sets if a in s);sb=next(s for s in sets if b in s)
        d.union(a,b)
        if sa is not sb:sets.remove(sa);sets.remove(sb);sets.append(sa|sb)
        for x in range(20):
            for y in range(20):assert (d.find(x)==d.find(y))==any(x in s and y in s for s in sets)
    print("PASS: 32000 Fenwick comparisons, 80000 DSU connectivity comparisons")
if __name__=='__main__':main()
