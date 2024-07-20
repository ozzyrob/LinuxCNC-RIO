import os
import sys
import json

from .buildsys import *
from .testbench import testbench


def verilog_top(project):
    top_arguments = []
    for pname in sorted(list(project["pinlists"])):
        pins = project["pinlists"][pname]
        for pin in pins:
            if pin[1].startswith("EXPANSION"):
                continue
            if pin[1] == "USRMCLK":
                continue
            top_arguments.append(f"{pin[2].lower()} {pin[0]}")

    top_data = []
    top_data.append("/*")
    top_data.append(f"    ######### {project['jdata']['name']} #########")
    top_data.append("")
    for key in (
        "toolchain",
        "family",
        "type",
        "package",
    ):
        value = project["jdata"].get(key)
        if value:
            top_data.append(f"    {key.title():10s}: {value}")
    top_data.append(
        f"    Clock     : {float(project['jdata']['clock']['speed']) / 1000000} Mhz"
    )
    top_data.append("")
    top_data.append("*/")
    top_data.append("")
    top_data.append("/* verilator lint_off UNUSEDSIGNAL */")
    top_data.append("")

    argsstr = ",\n        ".join(top_arguments)
    top_data.append(f"module rio (\n        {argsstr}")
    top_data.append("    );")
    top_data.append("")
    top_data.append("")

    if project["internal_clock"]:
        if project["jdata"].get("toolchain") == "diamond":
            top_data.append("    // Internal Oscillator")
            top_data.append("    wire sysclk;")
            top_data.append(f"    defparam OSCH_inst.NOM_FREQ = \"{int(project['jdata']['clock']['speed']) / 1000000}\";")
            top_data.append("    OSCH OSCH_inst ( ")
            top_data.append("        .STDBY(1'b0),")
            top_data.append("        .OSC(sysclk),")
            top_data.append("        .SEDSTDBY()")
            top_data.append("    );")
            top_data.append("")
        else:
            top_data.append("    // using internal oscillator")
            top_data.append("    wire sysclk;")
            top_data.append("    OSC osc(")
            top_data.append("    	.OSCOUT(sysclk)")
            top_data.append("    );")
            top_data.append("    defparam osc.FREQ_DIV=10;")
            top_data.append("")

    if project["jdata"]["interface"]:
        top_data.append("    reg ESTOP = 0;")
        top_data.append("    wire ERROR;")
        top_data.append("    wire INTERFACE_TIMEOUT;")
        top_data.append("    assign ERROR = (INTERFACE_TIMEOUT | ESTOP);")

    if project["osc_clock"]:
        top_data.append("    wire sysclk;")
        top_data.append("    wire locked;")

        if project["jdata"]["family"] == "MAX 10":
            top_data.append("    pll mypll(.inclk0(sysclk_in), .c0(sysclk), .locked(locked));")
        else:
            top_data.append("    pll mypll(sysclk_in, sysclk, locked);")

        top_data.append("")

    for pname, pins in project["pinlists"].items():
        if not pins:
            continue
        for pin in pins:
            if pin[1] == "USRMCLK":
                top_data.append(f"    wire {pin[0]};")
                top_data.append("    wire tristate_usrmclk = 1'b0;")
                top_data.append(
                    f"    USRMCLK u1 (.USRMCLKI({pin[0]}), .USRMCLKTS(tristate_usrmclk));"
                )
                top_data.append("")

    if "blink" in project["jdata"]:
        top_data.append(
            f"    blink #({int(project['jdata']['clock']['speed']) // 1 // 2}) blink1 ("
        )
        top_data.append("        .clk (sysclk),")
        top_data.append("        .led (BLINK_LED)")
        top_data.append("    );")
        top_data.append("")
        project["verilog_files"].append("blink.v")
        os.system(
            f"cp -a generators/gateware/blink.v* {project['SOURCE_PATH']}/blink.v"
        )

    if "error" in project["jdata"]:
        if project["jdata"]["error"].get("invert"):
            top_data.append("    assign ERROR_OUT = ~ERROR;")
        else:
            top_data.append("    assign ERROR_OUT = ERROR;")
        top_data.append("")

    if project["jdata"]["interface"]:
        top_data.append(f"    parameter BUFFER_SIZE = 16'd{project['data_size']}; // {project['data_size']// 8} bytes")
        top_data.append("")

        top_data.append(f"    wire[{project['data_size'] - 1}:0] rx_data;")
        top_data.append(f"    wire[{project['data_size'] - 1}:0] tx_data;")
        top_data.append("")

        top_data.append("    reg signed [31:0] header_tx;")
        top_data.append("    always @(posedge sysclk) begin")
        top_data.append("        if (ESTOP) begin")
        top_data.append("            header_tx <= 32'h65737470;")
        top_data.append("        end else begin")
        top_data.append("            header_tx <= 32'h64617461;")
        top_data.append("        end")
        top_data.append("    end")
        top_data.append("")

    # plugins wire/register definitions
    for plugin in project["plugins"]:
        if hasattr(project["plugins"][plugin], "defs"):
            defs = project["plugins"][plugin].defs()
            if defs:
                top_data.append("")
                top_data.append("")
                top_data.append(f"    // {plugin}")
                top_data += defs

    # expansion wires
    expansion_size = {}
    for expansions in project["expansions"].values():
        for enum, size in expansions.items():
            expansion_size[enum] = size
    expansion_ports = {}
    for pname, pins in project["pinlists"].items():
        for pin in pins:
            if pin[1].startswith("EXPANSION"):
                port = pin[1].split("[")[0]
                pnum = int(pin[1].split("[")[1].split("]")[0])
                size = expansion_size[port]
                if port.endswith("_OUTPUT"):
                    if port not in expansion_ports:
                        expansion_ports[port] = {}
                        for n in range(size):
                            expansion_ports[port][n] = "1'd0"
                if pin[2] == "OUTPUT":
                    if "_OUTPUT" not in pin[1]:
                        print("ERROR: pin-direction do not match:", pin)
                        exit(1)
                    expansion_ports[port][pnum] = pin[0]
                else:
                    if "_INPUT" not in pin[1]:
                        print("ERROR: pin-direction do not match:", pin)
                        exit(1)
    # top_data.append("")

    for pname, pins in project["pinlists"].items():
        for pin in pins:
            if pin[1].startswith("EXPANSION"):
                if pin[2] == "OUTPUT":
                    top_data.append(f"    wire {pin[0]};")
                else:
                    top_data.append(f"    wire {pin[0]};")

    jointEnables = []
    for num, joint in enumerate(project["jointnames"]):
        top_data.append(f"    wire {joint['_prefix']}Enable;")
        jointEnables.append(f"{joint['_prefix']}Enable")

    if "enable" in project["jdata"]:
        jointEnablesStr = " || ".join(jointEnables)
        if project["jdata"]["enable"].get("invert", False):
            top_data.append(f"    wire ENA_INV;")
            top_data.append(f"    assign ENA = ~ENA_INV;")
            if jointEnablesStr:
                top_data.append(f"    assign ENA_INV = ({jointEnablesStr}) && ~ERROR;")
        else:
            if jointEnablesStr:
                top_data.append(f"    assign ENA = ({jointEnablesStr}) && ~ERROR;")
            else:
                top_data.append(f"    assign ENA = ~ERROR;")
        top_data.append("")

    if project["voutnames"]:
        top_data.append(f"    // vouts {project['vouts']}")
        for num, vout in enumerate(project["voutnames"]):
            top_data.append(f"    wire signed [31:0] {vout['_prefix']};")
        top_data.append("")

    if project["vinnames"]:
        top_data.append(f"    // vins {project['vins']}")
        for num, vin in enumerate(project["vinnames"]):
            bits = vin.get("_bits", 32)
            top_data.append(f"    wire signed [{bits-1}:0] {vin['_prefix']};")
        top_data.append("")

    if project["jointnames"]:
        top_data.append(f"    // joints {project['joints']}")
        for num, joint in enumerate(project["jointnames"]):
            top_data.append(f"    wire signed [31:0] {joint['_prefix']}FreqCmd;")
        for num, joint in enumerate(project["jointnames"]):
            top_data.append(f"    wire signed [31:0] {joint['_prefix']}Feedback;")
        top_data.append("")

    if project["binnames"]:
        top_data.append(f"    // bins {project['bins']}")
        for num, bins in enumerate(project["binnames"]):
            top_data.append(
                f"    wire signed [{bins['size'] - 1}:0] {bins['_prefix']};"
            )
        top_data.append("")

    if project["boutnames"]:
        top_data.append(f"    // bouts {project['bouts']}")
        for num, bout in enumerate(project["boutnames"]):
            top_data.append(
                f"    wire signed [{bout['size'] - 1}:0] {bout['_prefix']};"
            )
        top_data.append("")

    if project["jdata"]["interface"]:
        top_data.append(f"    // rx_data {project['rx_data_size']}")
        pos = project["data_size"]

        top_data.append("    // wire [31:0] header_rx;")
        top_data.append(
            f"    // assign header_rx = {{rx_data[{pos-3*8-1}:{pos-3*8-8}], rx_data[{pos-2*8-1}:{pos-2*8-8}], rx_data[{pos-1*8-1}:{pos-1*8-8}], rx_data[{pos-1}:{pos-8}]}};"
        )
        pos -= 32

        for num, joint in enumerate(project["jointnames"]):
            top_data.append(
                f"    assign {joint['_prefix']}FreqCmd = {{rx_data[{pos-3*8-1}:{pos-3*8-8}], rx_data[{pos-2*8-1}:{pos-2*8-8}], rx_data[{pos-1*8-1}:{pos-1*8-8}], rx_data[{pos-1}:{pos-8}]}};"
            )
            pos -= 32

        for num, vout in enumerate(project["voutnames"]):
            top_data.append(
                f"    assign {vout['_prefix']} = {{rx_data[{pos-3*8-1}:{pos-3*8-8}], rx_data[{pos-2*8-1}:{pos-2*8-8}], rx_data[{pos-1*8-1}:{pos-1*8-8}], rx_data[{pos-1}:{pos-8}]}};"
            )
            pos -= 32

        for num, bout in enumerate(project["boutnames"]):
            boutsize = bout["size"]
            pack = []
            for bn in range(boutsize // 8):
                pack.append(f"rx_data[{pos-1}:{pos-8}]")
                pos -= 8
            pack.reverse()
            top_data.append(f"    assign {bout['_prefix']} = {{{', '.join(pack)}}};")

        for dbyte in range(project["joints_en_total"] // 8):
            for num in range(8):
                bitnum = dbyte * 8 + (7 - num)
                if bitnum < project["joints"]:
                    jname = project["jointnames"][bitnum]["_prefix"]
                    top_data.append(f"    assign {jname}Enable = rx_data[{pos-1}];")
                pos -= 1

        for dbyte in range(project["douts_total"] // 8):
            for num in range(8):
                bitnum = num + (dbyte * 8)
                if bitnum < project["douts"]:
                    dname = project["doutnames"][bitnum]["_prefix"]
                    if project["doutnames"][bitnum].get("invert", False):
                        top_data.append(f"    assign {dname} = ~rx_data[{pos-1}];")
                    else:
                        top_data.append(f"    assign {dname} = rx_data[{pos-1}];")
                else:
                    top_data.append(f"    // assign DOUTx = rx_data[{pos-1}];")
                pos -= 1

        # top_data.append("")
        top_data.append(f"    // tx_data {project['tx_data_size']}")
        top_data.append("    assign tx_data = {")
        top_data.append(
            "        header_tx[7:0], header_tx[15:8], header_tx[23:16], header_tx[31:24],"
        )

        for num, joint in enumerate(project["jointnames"]):
            top_data.append(
                f"        {joint['_prefix']}Feedback[7:0], {joint['_prefix']}Feedback[15:8], {joint['_prefix']}Feedback[23:16], {joint['_prefix']}Feedback[31:24],"
            )

        for bitsize in (32, 16, 8):
            for num, vin in enumerate(project["vinnames"]):
                bits = vin.get("_bits", 32)
                if bitsize != bits:
                    continue
                block = []
                for bit in range(0, bits, 8):
                    block.append(f"{vin['_prefix']}[{bit+7}:{bit}]")
                top_data.append(f"        {', '.join(block)}, ")

        for num, bins in enumerate(project["binnames"]):
            binsize = bins["size"]
            pack = []
            for bn in range(binsize // 8):
                pack.append(f"{bins['_prefix']}[{(bn * 8)+7}:{(bn * 8)}]")
            top_data.append(f"        {', '.join(pack)},")

        tdins = []
        ldin = project["dins"]
        for dbyte in range(project["dins_total"] // 8):
            for num in range(8):
                bitnum = num + (dbyte * 8)
                if bitnum < project["dins"]:
                    dname = project["dinnames"][bitnum]["_prefix"]
                    din_data = project["dinnames"][bitnum]
                    if bitnum < ldin and din_data.get("invert", False):
                        tdins.append(f"~{dname}")
                    else:
                        tdins.append(f"{dname}")
                else:
                    tdins.append(f"1'd0")

        fill = project["data_size"] - project["tx_data_size"]

        if fill > 0:
            top_data.append(f"        {', '.join(tdins)},")
            top_data.append(f"        {fill}'d0")
        else:
            top_data.append(f"        {', '.join(tdins)}")
        top_data.append("    };")
        # top_data.append("")

        for pname, pins in project["pinlists"].items():
            for pin in pins:
                if pin[1].startswith("EXPANSION"):
                    if pin[2] == "INPUT":
                        top_data.append(f"    assign {pin[0]} = {pin[1]};")
        for port, pins in expansion_ports.items():
            assign_list = []
            size = expansion_size[port]
            for n in range(size):
                assign_list.append(f"{pins[size - 1 - n]}")
            top_data.append(f"    assign {port} = {{{', '.join(assign_list)}}};")

    for plugin in project["plugins"]:
        if hasattr(project["plugins"][plugin], "funcs"):
            funcs = project["plugins"][plugin].funcs()
            if funcs:
                top_data.append("")
                top_data.append(f"    // {plugin}")
                top_data += funcs

    top_data.append("endmodule")
    top_data.append("")
    open(f"{project['SOURCE_PATH']}/rio.v", "w").write("\n".join(top_data))
    project["verilog_files"].append("rio.v")


def generate(project):
    print("generating gateware")

    # general verilog-files
    project["verilog_files"].append("debouncer.v")
    os.system(
        f"cp -a generators/gateware/debouncer.v* {project['SOURCE_PATH']}/debouncer.v"
    )

    # system clock (pll setup)
    if project["internal_clock"]:
        pass
    elif project["osc_clock"]:
        if int(project["jdata"]["clock"]["speed"]) < int(project["osc_clock"]):
            divider_val = int(project["osc_clock"]) // int(
                project["jdata"]["clock"]["speed"]
            )
            divider = []
            divider.append("")
            divider.append("module pll(")
            divider.append("        input sysclk_in,")
            divider.append("        output reg sysclk,")
            divider.append("        output reg locked")
            divider.append("    );")
            divider.append("")
            divider.append("    reg[27:0] counter=28'd0;")
            divider.append(f"    parameter DIVISOR = 28'd{divider_val};")
            divider.append("    always @(posedge sysclk_in) begin")
            divider.append("        counter <= counter + 28'd1;")
            divider.append("        if(counter>=(DIVISOR-1)) begin")
            divider.append("            counter <= 28'd0;")
            divider.append("        end")
            divider.append("        sysclk <= (counter<DIVISOR/2)?1'b1:1'b0;")
            divider.append("    end")
            divider.append("endmodule")
            divider.append("")
            divider.append("")
            open(f"{project['SOURCE_PATH']}/pll.v", "w").write("\n".join(divider))
        elif project["jdata"]["family"] == "ecp5":
            os.system(
                f"ecppll -f '{project['SOURCE_PATH']}/pll.v' -i {float(project['osc_clock']) / 1000000} -o {float(project['jdata']['clock']['speed']) / 1000000}"
            )
        elif project["jdata"]["type"] == "up5k":
            os.system(
                f"icepll -p -m -f '{project['SOURCE_PATH']}/pll.v' -i {float(project['osc_clock']) / 1000000} -o {float(project['jdata']['clock']['speed']) / 1000000}"
            )
        elif project["jdata"]["family"] == "GW1N-9C":
            os.system(
                f"python3 files/gowin-pll.py -d 'GW1NR-9 C6/I5' -f '{project['SOURCE_PATH']}/pll.v' -i {float(project['osc_clock']) / 1000000} -o {float(project['jdata']['clock']['speed']) / 1000000}"
            )
        elif project["jdata"]["family"] == "MAX 10":
            os.system(
                f"files/quartus-pll.sh \"{project['jdata']['family']}\" {float(project['osc_clock']) / 1000000} {float(project['jdata']['clock']['speed']) / 1000000} '{project['SOURCE_PATH']}/pll.v'"
            )
        else:
            os.system(
                f"icepll -q -m -f '{project['SOURCE_PATH']}/pll.v' -i {float(project['osc_clock']) / 1000000} -o {float(project['jdata']['clock']['speed']) / 1000000}"
            )
        project["verilog_files"].append("pll.v")

    verilog_top(project)
    testbench(project)

    # build files (makefiles/scripts/projects)
    board = project["jdata"].get("board")

    # generate makefiles
    if board in {"TangNano9K", "TangNano20K", "TangPrimer20K"}:
        buildsys_gowin(project)
    elif project["jdata"].get("toolchain") == "icestorm":
        buildsys_icestorm(project)
    elif project["jdata"].get("toolchain") == "vivado":
        buildsys_vivado(project)
    elif project["jdata"].get("toolchain") == "ise":
        buildsys_ise(project)
    elif project["jdata"].get("toolchain") == "quartus":
        buildsys_quartus(project)
    elif project["jdata"].get("toolchain") == "diamond":
        buildsys_diamond(project)
    elif project["jdata"].get("toolchain") == "verilator":
        buildsys_verilator(project)

    # backup active configuration
    open(f"{project['SOURCE_PATH']}/config.json", "w").write(json.dumps(project["jdata"], indent=2))
