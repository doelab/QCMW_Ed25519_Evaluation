# Core 0 (bottom-left)
create_pblock pblock_core0
add_cells_to_pblock [get_pblocks pblock_core0] [get_cells -hierarchical -filter {NAME =~ *u_core0*}]
resize_pblock [get_pblocks pblock_core0] -add {SLICE_X0Y0:SLICE_X35Y74}
resize_pblock [get_pblocks pblock_core0] -add {DSP48_X0Y0:DSP48_X0Y49}

# Core 1 (bottom-right)
create_pblock pblock_core1
add_cells_to_pblock [get_pblocks pblock_core1] [get_cells -hierarchical -filter {NAME =~ *u_core1*}]
resize_pblock [get_pblocks pblock_core1] -add {SLICE_X36Y0:SLICE_X75Y74}
resize_pblock [get_pblocks pblock_core1] -add {DSP48_X1Y0:DSP48_X1Y49}

# Core 2 (top-left)
create_pblock pblock_core2
add_cells_to_pblock [get_pblocks pblock_core2] [get_cells -hierarchical -filter {NAME =~ *u_core2*}]
resize_pblock [get_pblocks pblock_core2] -add {SLICE_X0Y75:SLICE_X35Y149}
resize_pblock [get_pblocks pblock_core2] -add {DSP48_X0Y50:DSP48_X0Y99}

# Core 3 (top-right)
create_pblock pblock_core3
add_cells_to_pblock [get_pblocks pblock_core3] [get_cells -hierarchical -filter {NAME =~ *u_core3*}]
resize_pblock [get_pblocks pblock_core3] -add {SLICE_X36Y75:SLICE_X75Y149}
resize_pblock [get_pblocks pblock_core3] -add {DSP48_X1Y50:DSP48_X1Y99}
