class Plugin:
    def __init__(self, jdata):
        self.jdata = jdata

    def setup(self):
        return [
            {
                "basetype": "vout",
                "subtype": "sine",
                "options": {
                    "pin": {
                        "type": "output",
                        "name": "output pin",
                    },
                },
            }
        ]

    def pinlist(self):
        pinlist_out = []
        for num, vout in enumerate(self.jdata["vout"]):
            if vout["type"] == "sine":
                if "pins" in vout:
                    for pn, pin in enumerate(vout["pins"]):
                        pinlist_out.append((f"VOUT{num}_SINEPWM_{pn}", pin, "OUTPUT"))
                else:
                    pinlist_out.append((f"VOUT{num}_SINEPWM", vout["pin"], "OUTPUT"))
        return pinlist_out



    def variables(self):
        variables = []
        for num, vout in enumerate(self.jdata["vout"]):
            if vout["type"] == "sine":
                variables.append({"dir": "OUT", "type": "VARIABLE", "calc": "frequency", "size": 32, "vout": num})
        return variables


    def vouts(self):
        vouts_out = 0
        for _num, vout in enumerate(self.jdata["vout"]):
            if vout["type"] == "sine":
                vouts_out += 1
        return vouts_out


    def funcs(self):
        func_out = ["    // vout_sinepwm's"]
        for num, vout in enumerate(self.jdata["vout"]):
            if vout["type"] == "sine":
                frequency = int(vout.get("frequency", 100000))
                #divider = int(self.jdata["clock"]["speed"]) // frequency // 2
                divider = 255
                if "pins" in vout:
                    pstep = 30 // len(vout["pins"])
                    start = 0
                    for pn, _pin in enumerate(vout["pins"]):
                        func_out.append(
                            f"    vout_sinepwm #({start}, {divider}) vout_sinepwm{num}_{pn} ("
                        )
                        func_out.append("        .clk (sysclk),")
                        func_out.append(f"        .freq (setPoint{num}),")
                        func_out.append(f"        .pwm_out (VOUT{num}_SINEPWM_{pn})")
                        func_out.append("    );")
                        start = start + pstep

                else:
                    start = vout.get("start", 0)
                    func_out.append(f"    vout_sinepwm #({start}, {divider}) vout_sinepwm{num} (")
                    func_out.append("        .clk (sysclk),")
                    func_out.append(f"        .freq (setPoint{num}),")
                    func_out.append(f"        .pwm_out (VOUT{num}_SINEPWM)")
                    func_out.append("    );")
        return func_out

    def ips(self):
        for num, vout in enumerate(self.jdata["vout"]):
            if vout["type"] in ["sine"]:
                return ["vout_sinepwm.v"]
        return []
