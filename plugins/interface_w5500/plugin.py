class Plugin:
    def __init__(self, jdata):
        self.jdata = jdata

    def setup(self):
        return [
            {
                "basetype": "interface",
                "subtype": "w5500",
                "comment": "w5500 interface for the communication with LinuxCNC",
                "options": {
                    "pins": {
                        "type": "dict",
                        "name": "pin config",
                        "options": {
                            "MOSI": {
                                "type": "input",
                                "name": "mosi pin",
                            },
                            "MISO": {
                                "type": "output",
                                "name": "miso pin",
                            },
                            "SCK": {
                                "type": "input",
                                "name": "clock pin",
                            },
                            "SEL": {
                                "type": "input",
                                "name": "selectionpin",
                            },
                        },
                    },
                },
            }
        ]

    def pinlist(self):
        pinlist_out = []
        for num, interface in enumerate(self.jdata.get("interface", [])):
            if interface["type"] == "w5500":
                pinlist_out.append(
                    ("INTERFACE_W5500_MOSI", interface["pins"]["MOSI"], "OUTPUT")
                )
                pinlist_out.append(
                    ("INTERFACE_W5500_MISO", interface["pins"]["MISO"], "INPUT")
                )
                pinlist_out.append(
                    ("INTERFACE_W5500_SCK", interface["pins"]["SCK"], "OUTPUT")
                )
                pinlist_out.append(
                    ("INTERFACE_W5500_SSEL", interface["pins"]["SEL"], "OUTPUT")
                )
        return pinlist_out

    def funcs(self):
        func_out = []
        for num, interface in enumerate(self.jdata.get("interface", [])):
            if interface["type"] == "w5500":
                mac = interface.get("mac", "AA:AF:FA:CC:E3:1C").split(":")
                mac_addr = f"{{8'h{mac[0]}, 8'h{mac[1]}, 8'h{mac[2]}, 8'h{mac[3]}, 8'h{mac[4]}, 8'h{mac[5]}}}"
                ip = interface.get("ip", "192.168.10.193").split(".")
                ip_addr = f"{{8'd{ip[0]}, 8'd{ip[1]}, 8'd{ip[2]}, 8'd{ip[3]}}}"
                port = interface.get("port", 2390)

                func_out.append("    interface_w5500 #(")
                func_out.append("        .BUFFER_SIZE(BUFFER_SIZE),")
                func_out.append("        .MSGID(32'h74697277),")
                func_out.append(f"        .TIMEOUT(32'd{int(self.jdata['clock']['speed']) // 4}),")
                func_out.append(f"        .MAC_ADDR({mac_addr}),")
                func_out.append(f"        .IP_ADDR({ip_addr}),")
                func_out.append(f"        .PORT({port})")
                func_out.append("    ) w55001(")
                func_out.append("        .clk (sysclk),")
                func_out.append("        .W5500_SCK (INTERFACE_W5500_SCK),")
                func_out.append("        .W5500_SSEL (INTERFACE_W5500_SSEL),")
                func_out.append("        .W5500_MOSI (INTERFACE_W5500_MOSI),")
                func_out.append("        .W5500_MISO (INTERFACE_W5500_MISO),")
                func_out.append("        .rx_data (rx_data),")
                func_out.append("        .tx_data (tx_data),")
                func_out.append("        .pkg_timeout (INTERFACE_TIMEOUT)")
                func_out.append("    );")
        return func_out

    def ips(self):
        for num, interface in enumerate(self.jdata.get("interface", [])):
            if interface["type"] == "w5500":
                return ["interface_w5500.v"]
        return []
