`timescale 1ns/1ps
`default_nettype none
module tb_slot;
 parameter integer WIDTH=8;
 reg clk=0;
 always #5 clk=~clk;
 reg rst_n=1, s_valid=0, m_ready=0;
 reg [WIDTH-1:0] s_data=0;
 wire s_ready,m_valid;
 wire [WIDTH-1:0] m_data;
 elastic_slot #(.WIDTH(WIDTH)) dut(.*);
 reg [WIDTH-1:0] history[0:8191];
 integer accepted=0, delivered=0, epoch=0, cycles=0;
 integer pushes=0,pops=0,replaces=0,stalls=0;
 reg pre_push,pre_pop;
 reg [WIDTH-1:0] pre_word;
 reg [31:0] rng=32'h205017;
 reg [1023:0] vcd_path;
 reg chosen_valid;
 reg [WIDTH-1:0] chosen_word;
 task check_queue;
  begin
   if(m_valid !== (accepted>delivered))
    $fatal(1,"occupancy mismatch t=%0t epoch=%0d",$time,epoch);
   if(accepted-delivered>1 || accepted<delivered)
    $fatal(1,"capacity/count mismatch");
   if(m_valid && m_data !== history[delivered])
    $fatal(1,"head mismatch t=%0t expected=%h actual=%h",$time,history[delivered],m_data);
  end
 endtask
 task tick(input reg sv,input reg [WIDTH-1:0] word,input reg mr);
  begin
   @(negedge clk); s_valid=sv; s_data=word; m_ready=mr;
   #1; check_queue;
   pre_push=s_valid && s_ready; pre_pop=m_valid && m_ready; pre_word=s_data;
   if(m_valid && !m_ready) stalls=stalls+1;
   if(pre_push && pre_pop) replaces=replaces+1;
   @(posedge clk);
   // Transactions are defined from the PRE-edge sampled ports. Remove old before append new.
   if(pre_pop) begin delivered=delivered+1;pops=pops+1;end
   if(pre_push) begin history[accepted]=pre_word;accepted=accepted+1;pushes=pushes+1;end
   cycles=cycles+1;
   #1; check_queue; // 1 ns after NBA, no input drive at the sampling edge
  end
 endtask
 task flush;
  begin
   @(negedge clk); #2; rst_n=0; s_valid=0;m_ready=0;
   accepted=0;delivered=0;epoch=epoch+1;
   #1;
   if(s_ready!==0 || m_valid!==0 || m_data!==0) $fatal(1,"async flush failed");
   @(negedge clk); rst_n=1;
   @(posedge clk); #1; check_queue;
  end
 endtask
 integer i;
 initial begin
  if(!$value$plusargs("VCD=%s",vcd_path)) $fatal(1,"explicit +VCD=/absolute/output/file.vcd required");
  $dumpfile(vcd_path); $dumpvars(0,tb_slot);
  #1;rst_n=0;#1;
  if(s_ready!==0 || m_valid!==0 || m_data!==0) $fatal(1,"initial reset failed");
  @(negedge clk);rst_n=1;
  tick(1,8'hA1,1);tick(1,8'hB2,0);tick(1,8'hB2,0);
  tick(1,8'hB2,1);tick(0,0,1);tick(0,0,1);
  tick(1,8'h55,0);flush;
  // Source holds a pending word whenever backpressured. Reproducible local LFSR.
  for(i=0;i<1000;i=i+1) begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   chosen_valid=s_valid;chosen_word=s_data;
   if(!(s_valid && !pre_push)) begin chosen_valid=rng[0];chosen_word=rng[WIDTH:1];end
   tick(chosen_valid,chosen_word,rng[17]);
  end
  if(replaces==0 || stalls==0 || pushes==0 || pops==0) $fatal(1,"coverage missing");
  $display("PASS cycles=%0d pushes=%0d pops=%0d replace=%0d stalls=%0d epochs=%0d seed=205017",cycles,pushes,pops,replaces,stalls,epoch);
  $finish;
 end
 initial begin #20000;$fatal(1,"finite simulation timeout");end
endmodule
`default_nettype wire
