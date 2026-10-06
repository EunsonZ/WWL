from collections import deque
from fractions import Fraction

def fifo(refs,capacity):
    if capacity<=0:raise ValueError("capacity")
    resident=set();queue=deque();faults=0
    for page in refs:
        if page not in resident:
            faults+=1
            if len(resident)==capacity:resident.remove(queue.popleft())
            resident.add(page);queue.append(page)
    return faults

def safe_sequence(available,alloc,need):
    work=available[:];done=set();order=[]
    while len(done)<len(alloc):
        for i in range(len(alloc)):
            if i not in done and all(n<=w for n,w in zip(need[i],work)):
                work=[w+a for w,a in zip(work,alloc[i])];done.add(i);order.append(i);break
        else:return None
    return order

def main():
    refs=[1,2,3,4,1,2,5,1,2,3,4,5]
    assert fifo(refs,3)==9 and fifo(refs,4)==10
    assert safe_sequence([1,1],[[1,0],[0,1]],[[1,1],[2,0]])==[0,1]
    assert safe_sequence([0,1],[[1,0],[1,1]],[[1,1],[1,0]]) is None
    def stats(order):
        now=0;wait=0;turn=0
        for burst in order:wait+=now;now+=burst;turn+=now
        return Fraction(wait,len(order)),Fraction(turn,len(order))
    assert stats([8,4,1])==(Fraction(20,3),Fraction(11))
    assert stats([1,4,8])==(Fraction(2),Fraction(19,3))
    print("PASS: FIFO Belady 9/10, safe/unsafe banker states, FCFS/SJF exact fractions")
if __name__=='__main__':main()
