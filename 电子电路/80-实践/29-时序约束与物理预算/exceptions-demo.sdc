# Source only after a separately reviewed same-waveform two-cycle enable protocol.
# This demo does NOT authorize changing timing_top's every-edge behavior.
if {![info exists ENABLE_PROTOCOL_REVIEWED] || !$ENABLE_PROTOCOL_REVIEWED} {
 error "Two-cycle source/receiver enable protocol not established"
}
# Require caller-selected genuine startpoint and endpoint names in another design.
if {![info exists MC_START] || ![info exists MC_END]} {error "MC endpoints absent"}
set_multicycle_path 2 -setup -from [get_pins $MC_START] -to [get_pins $MC_END]
set_multicycle_path 1 -hold -end -from [get_pins $MC_START] -to [get_pins $MC_END]
