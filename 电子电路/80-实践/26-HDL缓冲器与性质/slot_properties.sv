`default_nettype none
module slot_properties(input wire clk);
 localparam WIDTH=2;
 (* anyseq *) reg rst_n,s_valid,m_ready;
 (* anyseq *) reg [WIDTH-1:0] s_data;
 wire s_ready,m_valid;wire [WIDTH-1:0] m_data;
 elastic_slot #(.WIDTH(WIDTH)) dut(.*);
 reg past_valid=0;
 reg occupied=0;
 reg [WIDTH-1:0] head=0;
 wire push=s_valid && s_ready, pop=m_valid && m_ready;
 always @(posedge clk) begin
  past_valid<=1;
  if(!past_valid) assume(!rst_n);
  // Environmental source obligation; reset cancels its pending transaction.
  if(past_valid && rst_n && $past(rst_n) && $past(s_valid && !s_ready)) begin
   assume(s_valid);assume(s_data==$past(s_data));
  end
  if(!rst_n) occupied<=0;
  else begin
   if(pop) occupied<=0;
   if(push) begin occupied<=1;head<=s_data;end
  end
  if(past_valid && rst_n && $past(rst_n)) begin
   assert(m_valid==occupied);
   if(push) assert(!occupied || pop);
   if(pop) assert(occupied);
   if(occupied) assert(m_data==head);
   if($past(m_valid && !m_ready)) begin
    assert(m_valid);assert(m_data==$past(m_data));
   end
  end
  if(!rst_n) begin assert(!s_ready);assert(!m_valid);end
  if(past_valid) begin
   cover(rst_n && push && pop);
   cover(rst_n && m_valid && !m_ready);
   cover(!rst_n && $past(m_valid));
  end
 end
endmodule
`default_nettype wire
