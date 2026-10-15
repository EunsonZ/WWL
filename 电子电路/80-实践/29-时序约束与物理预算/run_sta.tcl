# Run from a copied lab. Synthetic table models, NOT foundry characterized.
set lab [file dirname [file normalize [info script]]]
read_liberty -min [file join $lab cells-fast.lib]
read_liberty -max [file join $lab cells-slow.lib]
read_verilog [file join $lab timing_top.v]
link_design timing_top
read_sdc [file join $lab example.sdc]
check_setup
report_checks -path_delay min_max
