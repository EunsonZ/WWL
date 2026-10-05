// U5: one clock, one word, no fall-through. WIDTH must be >= 1.
// rst_n is local active-low reset: async assert, externally synchronized release.
// The integration owns reset synchronization, recovery/removal and CDC/RDC review.
module elastic_buffer #(parameter integer WIDTH = 8) (
    input logic clk, rst_n,
    input logic s_valid,
    output logic s_ready,
    input logic [WIDTH-1:0] s_data,
    output logic m_valid,
    input logic m_ready,
    output logic [WIDTH-1:0] m_data
);
    logic full;
    logic [WIDTH-1:0] data_q;
    logic push;
    assign s_ready = rst_n && (!full || m_ready);
    assign m_valid = rst_n && full;
    assign m_data = data_q;
    assign push = s_valid && s_ready;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            full <= 1'b0;
            data_q <= '0;
        end else if (s_ready) begin
            full <= s_valid;
            if (push) data_q <= s_data;
        end
    end
`ifdef U5_SVA
    // Safety over sampled edges; reset deliberately flushes the pending item.
    assert property (@(posedge clk) disable iff (!rst_n)
        (m_valid && !m_ready) |=> (m_valid && $stable(m_data)));
    assert property (@(posedge clk) disable iff (!rst_n)
        (!full) |-> (!m_valid));
`endif
endmodule
