# SPDX-License-Identifier: CC-BY-SA-4.0
TOPLEVEL_LANG ?= verilog
SIM ?= verilator
WAVES ?= 0

ifeq ($(WAVES),1)
EXTRA_ARGS += --trace --trace-structs
endif
EXTRA_ARGS += -Wno-WIDTH -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
              -Wno-ASCRANGE -Wno-CASEINCOMPLETE -Wno-INITIALDLY \
              -Wno-MULTIDRIVEN -Wno-LATCH -Wno-IMPLICIT -Wno-COMBDLY \
              -Wno-PROCASSWIRE -Wno-UNOPTFLAT \
              -Wno-IMPLICITSTATIC

PROJECT_ROOT = $(shell git rev-parse --show-toplevel)
MAST = $(PROJECT_ROOT)/mast

VERILOG_SOURCES = \
    $(MAST)/src/assert.sv \
    $(MAST)/src/op_const.sv \
    $(MAST)/src/const.sv \
    $(MAST)/src/int/int_div_regfile.sv \
    $(MAST)/src/float/float_params.sv \
    $(MAST)/src/float/float_add_pipeline.sv \
    $(MAST)/src/int/chunked_add_task.sv \
    $(MAST)/src/int/chunked_sub_task.sv \
    $(MAST)/src/generated/mul_pipeline_cycle_24bit_2bpc.sv \
    $(MAST)/src/float/float_mul_pipeline.sv \
    $(MAST)/src/generated/mul_pipeline_cycle_32bit_2bpc.sv \
    $(MAST)/src/int/mul_pipeline_32bit.sv \
    $(MAST)/src/core.sv \
    $(MAST)/src/popsolutions/axi4/axi4_const.sv \
    $(MAST)/src/popsolutions/axi4/axi4_mem_model.sv \
    $(MAST)/src/popsolutions/axi4/axi4_master_simple.sv \
    $(MAST)/src/popsolutions/axi4/core_axi4_adapter.sv \
    $(PROJECT_ROOT)/src/inner_jib_top.sv

TOPLEVEL = inner_jib_top
MODULE = test_inner_jib_top

include $(shell cocotb-config --makefiles)/Makefile.sim
