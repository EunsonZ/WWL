# Teaching Liberty units: ns, pF. No physical clock tree or extracted wire here.
create_clock -name core -period 10 -waveform {0 5} [get_ports clk]
set_clock_uncertainty -setup 0.2 [get_clocks core]
set_clock_uncertainty -hold 0.05 [get_clocks core]
set_input_delay -clock core -max 1.2 [get_ports a]
set_input_delay -clock core -min 0.2 [get_ports a]
set_input_transition 0.1 [get_ports {a async_in}]
set_output_delay -clock core -max 1.0 [get_ports {y sync_out}]
set_output_delay -clock core -min -0.2 [get_ports {y sync_out}]
set_load 0.020 [get_ports {y sync_out}]
# Only async source -> FIRST stage. Sync1/Q -> Sync2/D remains timed.
set_false_path -from [get_ports async_in] -to [get_pins u_sync1/D]
# No multicycle on ordinary every-edge flops.
