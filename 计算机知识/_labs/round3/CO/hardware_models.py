"""Teaching models: not a simulator of a named commercial processor."""
import math

def split_address(a):return (a>>13,(a>>6)&127,a&63)
def parity(bits):return sum(bits)&1

def main():
    assert split_address(0x12345678)==(0x91a2,0x59,0x38)
    for a in range(0,1<<16,7):
        tag,index,offset=split_address(a)
        assert (tag<<13)|(index<<6)|offset==a
    assert (0xABC<<12)|(0x12345&0xFFF)==0xABC345
    # Exhaustive full-adder truth table.
    for a in (0,1):
        for b in (0,1):
            for cin in (0,1):
                s=a^b^cin;carry=(a&b)|(a&cin)|(b&cin)
                assert s+2*carry==a+b+cin
    # SEC Hamming(7,4), even parity. Check every single-bit error for every data word.
    for data in range(16):
        c=[0]*8
        for bit,pos in enumerate((3,5,6,7)):c[pos]=(data>>bit)&1
        for p in (1,2,4):c[p]=parity([c[i] for i in range(1,8) if i&p and i!=p])
        for error in range(1,8):
            r=c[:];r[error]^=1
            syndrome=sum(p for p in (1,2,4) if parity([r[i] for i in range(1,8) if i&p]))
            assert syndrome==error;r[syndrome]^=1;assert r==c
    assert math.isclose(1/(1-.1),10/9)
    print("PASS: cache split/reassembly, page offset, 8 adder cases, 112 Hamming corrections")
if __name__=='__main__':main()
