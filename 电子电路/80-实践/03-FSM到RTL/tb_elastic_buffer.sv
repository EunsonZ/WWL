`timescale 1ns/1ps
module tb_elastic_buffer;
    logic clk=0, rst_n=0, s_valid=0, m_ready=0;
    logic [7:0] s_data=0, m_data;
    logic s_ready, m_valid;
    bit exp_full=0;
    logic [7:0] exp_data=0;
    bit accepted, popped;
    integer count=0, i;
    bit pending=0;
    logic [7:0] pending_data;
    logic [31:0] rng=32'h00510005;
    elastic_buffer #(.WIDTH(8)) dut(.*);
    always #5 clk=~clk;

    // Drive on falling edge. Check pre-edge outputs, then post-NBA registers.
    task automatic cycle(input bit sv, input logic [7:0] sd, input bit mr);
        @(negedge clk);
        s_valid=sv; s_data=sd; m_ready=mr;
        #1;
        assert(s_ready === (!exp_full || mr)) else $fatal(1,"ready");
        assert(m_valid === exp_full) else $fatal(1,"valid");
        if(exp_full) assert(m_data === exp_data) else $fatal(1,"ordering/stall");
        accepted=sv && s_ready;
        popped=m_valid && mr;
        // Independent one-place queue: remove old head BEFORE append new word.
        if(popped) exp_full=0;
        if(accepted) begin
            assert(!exp_full) else $fatal(1,"overflow");
            exp_full=1; exp_data=sd;
        end
        @(posedge clk); #1;
        assert(m_valid === exp_full) else $fatal(1,"post-edge valid");
        if(exp_full) assert(m_data === exp_data) else $fatal(1,"post-edge data");
        count=count+1;
    endtask
    task automatic flush;
        // Asynchronous assertion between edges; release away from active edge.
        @(negedge clk); #2;
        // Reset epoch cancels producer pending data as well as the buffered item.
        // Keep invalid through release and its intervening rising edge.
        s_valid=0; s_data=0; m_ready=0; pending=0;
        rst_n=0;
        #1;
        assert(!m_valid && !s_ready && m_data===8'h00) else $fatal(1,"reset");
        exp_full=0; exp_data=0;
        @(negedge clk); rst_n=1;
        @(posedge clk); #1;
        assert(!m_valid && s_ready && m_data===8'h00)
            else $fatal(1,"reset release gap accepted stale input");
    endtask
    initial begin
        // Initial 0 -> 1 -> 0 reset transition guarantees reset event in simulation.
        #1; rst_n=1; #1; rst_n=0;
        #1; assert(!m_valid && !s_ready) else $fatal(1,"reset gating");
        @(negedge clk); rst_n=1;
        cycle(1,8'hA1,1); // empty: input only, no fall-through
        cycle(1,8'hB2,0); cycle(1,8'hB2,0); // rejected B2 must remain pending
        cycle(1,8'hB2,1); // pop A1 and push B2 at same edge
        cycle(0,0,1); cycle(0,0,1);
        cycle(1,8'hCC,0); cycle(0,0,0); flush();
        cycle(1,8'hDD,1); cycle(0,0,1);
        for(i=0;i<5000;i=i+1) begin
            rng = (rng << 1) ^ (rng[31] ? 32'h00400007 : 0);
            if(!pending && rng[2]) begin pending=1; pending_data=rng[15:8]; end
            cycle(pending,pending ? pending_data : 0,rng[0]);
            if(accepted) pending=0;
            if(i%113==112) begin flush(); pending=0; end
        end
        cycle(pending,pending ? pending_data : 0,1);
        cycle(0,0,1); cycle(0,0,1);
        $display("PASS %0d cycles",count); $finish;
    end
    initial begin #1000000; $fatal(1,"timeout"); end
endmodule
