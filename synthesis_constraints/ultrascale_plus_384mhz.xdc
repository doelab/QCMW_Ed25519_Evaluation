# Clock
create_clock -period 2.600 -name clk [get_ports clk]

# I/O delays
set_input_delay -clock clk -max 0.500 [get_ports {rst start scalar[*] point_u[*]}]
set_input_delay -clock clk -min 0.000 [get_ports {rst start scalar[*] point_u[*]}]
set_output_delay -clock clk -max 0.500 [get_ports {done result_point[*]}]
set_output_delay -clock clk -min 0.000 [get_ports {done result_point[*]}]
