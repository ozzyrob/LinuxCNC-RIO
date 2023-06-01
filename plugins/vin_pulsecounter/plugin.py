class Plugin:
    def __init__(self, jdata):
        self.jdata = jdata

    def setup(self):
        return [
            {
                "basetype": "vin",
                "subtype": "counter",
                "comment": "counting signals on the input pins (up/down), can be reset by the reset-pin",
                "options": {
                    "pin_up": {
                        "type": "input",
                        "name": "up pin",
                        "comment": "to count up",
                    },
                    "pin_down": {
                        "type": "input",
                        "name": "down pin",
                        "comment": "to count down",
                    },
                    "pin_reset": {
                        "type": "input",
                        "name": "reset pin",
                        "comment": "reset the counter to zero",
                    },
                },
            }
        ]

    def pinlist(self):
        pinlist_out = []
        for num, vin in enumerate(self.jdata.get("vin", [])):
            if vin.get("type") in ("counter",):
                pullup = vin.get("pullup", False)
                if "pin_up" in vin:
                    pinlist_out.append(
                        (f"VIN{num}_PULSECOUNTER_UP", vin["pin_up"], "INPUT", pullup)
                    )
                if "pin_down" in vin:
                    pinlist_out.append(
                        (
                            f"VIN{num}_PULSECOUNTER_DOWN",
                            vin["pin_down"],
                            "INPUT",
                            pullup,
                        )
                    )
                if "pin_reset" in vin:
                    pinlist_out.append(
                        (
                            f"VIN{num}_PULSECOUNTER_RESET",
                            vin["pin_reset"],
                            "INPUT",
                            pullup,
                        )
                    )
        return pinlist_out


    def variables(self):
        variables = []
        for num, vin in enumerate(self.jdata.get("vin", [])):
            if vin["type"] == "counter":
                variables.append({"dir": "IN", "type": "VARIABLE", "calc": "linear", "size": 32, "vin": num})
        return variables


    def vins(self):
        vins_out = 0
        for _num, vin in enumerate(self.jdata.get("vin", [])):
            if vin.get("type") in ("counter",):
                vins_out += 1
        return vins_out

    def funcs(self):
        func_out = ["    // vin_pulsecounter's"]
        for num, vin in enumerate(self.jdata.get("vin", [])):
            if vin.get("type") in ("counter",):
                func_out.append(f"    vin_pulsecounter vin_pulsecounter{num} (")
                func_out.append("        .clk (sysclk),")
                func_out.append(f"        .counter (processVariable{num}),")
                if "pin_up" in vin:
                    func_out.append(f"        .UP (VIN{num}_PULSECOUNTER_UP),")
                else:
                    func_out.append("        .UP (1'd0),")
                if "pin_down" in vin:
                    func_out.append(f"        .DOWN (VIN{num}_PULSECOUNTER_DOWN),")
                else:
                    func_out.append("        .DOWN (1'd0),")
                if "pin_reset" in vin:
                    func_out.append(f"        .RESET (VIN{num}_PULSECOUNTER_RESET)")
                else:
                    func_out.append("        .RESET (1'd0)")
                func_out.append("    );")
        return func_out

    def ips(self):
        for num, vin in enumerate(self.jdata["vin"]):
            if vin["type"] in ["counter"]:
                return ["vin_pulsecounter.v"]
        return []
