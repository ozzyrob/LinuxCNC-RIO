class Plugin:
    def __init__(self, jdata):
        self.jdata = jdata

    def setup(self):
        return [
            {
                "basetype": "dout",
                "subtype": "",
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
        for num, dout in enumerate(self.jdata["dout"]):
            pinlist_out.append((f"DOUT{num}", dout["pin"], "OUTPUT"))
        return pinlist_out

    def variables(self):
        variables = []
        for num, dout in enumerate(self.jdata["dout"]):
            variables.append({"dir": "OUT", "type": "BIT", "size": 1, "dout": num})

        return variables

    def douts(self):
        douts_out = 0
        for _num, _pwmout in enumerate(self.jdata["dout"]):
            douts_out += 1
        return douts_out
