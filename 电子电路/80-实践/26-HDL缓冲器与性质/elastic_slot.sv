`timescale 1ns/1ps
`default_nettype none
module elastic_slot #(parameter integer WIDTH=8)(
 input wire clk, input wire rst_n,
 input wire s_valid, output wire s_ready, input wire [WIDTH-1:0] s_data,
 output wire m_valid, input wire m_ready, output wire [WIDTH-1:0] m_data);
 reg full;
 reg [WIDTH-1:0] data_q;
 wire push=s_valid && s_ready;
 assign s_ready=rst_n && (!full || m_ready);
 assign m_valid=rst_n && full;
 assign m_data=data_q;
`ifndef SYNTHESIS
`ifndef FORMAL
 initial if(WIDTH<1 || WIDTH>8) $fatal(1,"WIDTH must be 1..8");
`endif
`endif
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin full<=1'b0; data_q<={WIDTH{1'b0}}; end
  else begin
   if(s_ready) full<=s_valid;
`ifdef U26_FAULT_OVERWRITE
   if(s_valid) data_q<=s_data; // deliberate mutation: rejected input overwrites slot
`else
   if(push) data_q<=s_data;
`endif
  end
 end
endmodule
`default_nettype wire
