// Pure teaching gate netlist. No synthesized/placed/verified claim.
module timing_top(input clk,input a,input async_in,output y,output sync_out);
 wire q,n1,n2,s1;
 TDFF u_launch (.CK(clk),.D(a),.Q(q));
 TINV u_inv1 (.A(q),.Y(n1));
 TINV u_inv2 (.A(n1),.Y(n2));
 TDFF u_capture (.CK(clk),.D(n2),.Q(y));
 TDFF u_sync1 (.CK(clk),.D(async_in),.Q(s1));
 TDFF u_sync2 (.CK(clk),.D(s1),.Q(sync_out));
endmodule
