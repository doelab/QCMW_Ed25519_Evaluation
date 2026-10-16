# 100 MHz board clock
set_property -dict { PACKAGE_PIN E3 IOSTANDARD LVCMOS33 } [get_ports { clk_pin }]
create_clock -period 10.000 -name sys_clk_pin -waveform {0 5} [get_ports { clk_pin }]

# 10 MHz test clock
create_clock -period 100.000 -name clk [get_ports clk]

# Trigger out (PMOD JA1)
set_property -dict { PACKAGE_PIN C17 IOSTANDARD LVCMOS33 SLEW FAST } [get_ports { trigger_out }]

# Buttons & LEDs
set_property -dict { PACKAGE_PIN C12 IOSTANDARD LVCMOS33 } [get_ports { rst_n_pin }]
set_property -dict { PACKAGE_PIN N17 IOSTANDARD LVCMOS33 } [get_ports { btn_start_pin }]
set_property -dict { PACKAGE_PIN H17 IOSTANDARD LVCMOS33 } [get_ports { led_done }]
set_property -dict { PACKAGE_PIN K15 IOSTANDARD LVCMOS33 } [get_ports { led_pass }]
