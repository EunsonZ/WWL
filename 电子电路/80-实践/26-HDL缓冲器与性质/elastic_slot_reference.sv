`default_nettype none
module elastic_slot_reference #(parameter integer WIDTH=8)(
 input wire clk,rst_n,s_valid,m_ready,
 input wire [WIDTH-1:0] s_data,
 output wire s_ready,m_valid,
 output wire [WIDTH-1:0] m_data);
 reg full,next_full;
 reg [WIDTH-1:0] data_q,next_data;
 wire push=s_valid && s_ready;
 wire pop=m_valid && m_ready;
 assign s_ready=rst_n && (!full || m_ready);
 assign m_valid=rst_n && full;
 assign m_data=data_q;
 always @* begin
  next_full=push || (full && !pop);
  next_data=data_q;
  if(push) next_data=s_data;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin full<=0;data_q<=0;end
  else begin full<=next_full;data_q<=next_data;end
endmodule
`default_nettype wire
