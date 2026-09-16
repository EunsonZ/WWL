import ipaddress,struct,socket
class Frames:
    def __init__(self,limit=1024):self.buf=bytearray();self.limit=limit
    def feed(self,chunk):
        self.buf.extend(chunk);out=[]
        while len(self.buf)>=4:
            n=int.from_bytes(self.buf[:4],'big')
            if n>self.limit:raise ValueError('too large')
            if len(self.buf)<4+n:break
            out.append(bytes(self.buf[4:4+n]));del self.buf[:4+n]
        return out
    def finish(self):
        if self.buf:raise EOFError('truncated')
def crc(value,poly):
    while value and value.bit_length()>=poly.bit_length():value^=poly<<(value.bit_length()-poly.bit_length())
    return value

def main():
    messages=[b'hello',b'', '中文'.encode()]
    data=b''.join(struct.pack('!I',len(m))+m for m in messages)
    for split in range(len(data)+1):
        p=Frames();assert p.feed(data[:split])+p.feed(data[split:])==messages;p.finish()
    p=Frames();result=[]
    for b in data:result+=p.feed(bytes([b]))
    assert result==messages;p.finish()
    try:Frames(2).feed(struct.pack('!I',3))
    except ValueError:pass
    else:raise AssertionError('oversized frame accepted')
    p=Frames();p.feed(data[:-1])
    try:p.finish()
    except EOFError:pass
    else:raise AssertionError('truncated frame accepted')
    assert crc(0b1101<<3,0b1011)==1
    assert crc(0b1101001,0b1011)==0
    n=ipaddress.ip_network('192.0.2.130/26',strict=False)
    assert str(n.network_address)=='192.0.2.128' and str(n.broadcast_address)=='192.0.2.191'
    # Local AF_UNIX sockets only; no public listening port, no external network.
    a,b=socket.socketpair()
    try:
        a.settimeout(2);b.settimeout(2);a.sendall(data);a.shutdown(socket.SHUT_WR)
        p=Frames();received=[]
        while chunk:=b.recv(3):received+=p.feed(chunk)
        p.finish();assert received==messages
    finally:a.close();b.close()
    print("PASS: every two-way split, bytewise framing, EOF, limits, CRC, subnet, local sockets")
if __name__=='__main__':main()
