import copy
import unittest
from read_model import Node
from history_oracle import linearize
from run_lab import Memory


def leader():
    a,b=Node('A'),Node('B');req=a.elect();a.vote_ack(b.vote_request(req))
    return a,b

def commit(a,b,op='noop',value=None,wid=None):
    a.propose(op,value,wid);ack=b.append(a.make_append('B'));a.append_ack(ack)

class Barriers(unittest.TestCase):
    def test_current_term_and_apply_are_different_waits(self):
        a,b=leader();self.assertEqual(a.begin_read('r')['status'],'wait_current_term_commit')
        commit(a,b,'put',7,'w');a.begin_read('r');a.read_ack('r',b.probe(a.make_probe('r','B')))
        self.assertEqual(a.read_poll('r')['status'],'wait_apply');a.apply();self.assertEqual(a.read_poll('r')['value'],7)
    def test_nonce_is_fresh_and_duplicates_are_sets(self):
        a,b=leader();commit(a,b);a.apply();a.begin_read('r1');old=b.probe(a.make_probe('r1','B'))
        a.begin_read('r2');self.assertEqual(a.read_ack('r2',old)['status'],'nonce_or_term_mismatch')
        self.assertEqual(a.read_poll('r2')['status'],'wait_quorum')
        ack=b.probe(a.make_probe('r2','B'))
        for _ in range(10):a.read_ack('r2',ack)
        self.assertEqual(a.reads['r2']['acks'],['A','B'])
        self.assertEqual(a.begin_read('r2')['status'],'duplicate_read_id')
    def test_higher_term_cancels_before_old_reply_can_satisfy(self):
        a,b=leader();commit(a,b);a.apply();a.begin_read('r');ack=b.probe(a.make_probe('r','B'));ack['term']=a.term+1;ack['accepted']=False
        self.assertEqual(a.read_ack('r',ack)['status'],'cancelled_or_unknown');self.assertEqual(a.role,'follower')
    def test_boot_drops_read_context_but_preserves_log(self):
        a,b=leader();commit(a,b,'put',7,'w');a.apply();a.begin_read('r');p=a.persistent();again=Node('A',p)
        self.assertEqual(again.value,7);self.assertEqual(again.boot,a.boot+1);self.assertEqual(again.read_poll('r')['status'],'cancelled_or_unknown');self.assertEqual(again.role,'follower')
    def test_same_invocation_poll_has_one_response(self):
        a,b=leader();commit(a,b);a.apply();a.begin_read('r');a.read_ack('r',b.probe(a.make_probe('r','B')));first=a.read_poll('r')
        commit(a,b,'put',7,'w');a.apply();self.assertEqual(a.read_poll('r'),first)
    def test_read_read_order_not_only_write_precedence(self):
        h=[{'id':'w','client':'w','kind':'put','value':7,'start':1,'end':6},{'id':'r1','client':'r1','kind':'get','value':7,'start':2,'end':3},{'id':'r2','client':'r2','kind':'get','value':0,'start':4,'end':5}]
        self.assertIsNone(linearize(h))
        self.assertEqual(linearize([h[1]],[{**h[0],'end':None}]),['w','r1'])
    def test_invalid_peer_is_not_another_voter_or_partial_rpc(self):
        m=Memory(None);before=m.call('A','snapshot')
        with self.assertRaises(ValueError):m.call('A','vote_request',m={'source':'Z','term':99,'last':[0,0]})
        self.assertEqual(m.call('A','snapshot'),before)
    def test_bool_and_invalid_command_not_integer_protocol(self):
        a,b=leader()
        with self.assertRaises(ValueError):a.propose('put',True,'w')
        self.assertEqual(a.log,[])
        with self.assertRaises(ValueError):a.member('new-member')
if __name__=='__main__':unittest.main()
